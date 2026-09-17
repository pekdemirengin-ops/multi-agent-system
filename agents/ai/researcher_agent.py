"""Arastirma agent'i - coklu arama + baglam + LLM ozetleme."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient
from tools.web_search import search

logger = structlog.get_logger(__name__)


# ============================================================
# Sistem promptu - "uzman arastirmaci" gibi dusun
# ============================================================
SUMMARY_PROMPT = """Sen uzman bir arastirma asistanisin. Web arama sonuclarindan
EKSIKSIZ, HIZLI ve DOGRU cevap vereceksin.

ADIM ADIM DUSUN (kafandan, cevaba yazma):

ADIM 1: Soruyu parcala
- "Ronaldo kim, hangi takim, hoca kim" = 3 bilgi
- Her bilgi icin ayri dusun

ADIM 2: Her parca icin kaynaga bak
- Kaynaklari TEK TEK oku. Hicbirini ATLAMA.
- Kaynak basligi ilgili gorunuyorsa, icerigini OKU.
- Ornek: "Ronaldo yeni teknik direktoru" basligi -> ICERIKTE isim vardir.

ADIM 3: Cevabi yaz
- Her parca icin AYRI cumle
- MAKSIMUM 4 cumle
- SADECE kaynaktaki bilgi
- UYDURMA YOK

MUTLAK KURALLAR:
- Sorudaki HER parca icin cevap ver. Hicbirini atlama.
- Kaynagi ATLAMA. Her kaynak onemli olabilir.
- "Kaynakta yok" DEMEDEN ONCE tum kaynaklari kontrol et.
- Kaynaklarda OLMAYAN bilgiyi YAZMA. Uydurma YAPMA.
- Baglam: "Ronaldo'nun kulubu" -> Al-Nassr. "Portekiz milli takimi" -> ayri.
- Bilgi GERCEKTEN yoksa: "X bilgisi kaynaklarda yer almamaktadir"

ORNEK 1 (dogru cevap):
Soru: Cristiano Ronaldo kim, hangi takimda, hoca kim?
Kaynaklar:
  1. "Ronaldo 1985 Portekiz, Al-Nassr forvet"
  2. "Al-Nassr hocasi Ange Postecoglou, 3 Temmuz 2026"
  3. "Ronaldo nun yeni teknik direktoru belli oldu - beIN Sports"
Cevap: Cristiano Ronaldo, 1985 dogumlu Portekizli forvet oyuncusudur. Al-Nassr kulubunde oynamaktadir. Al-Nassr'in teknik direktoru Ange Postecoglou'dur.

ORNEK 2 (kaynakta bilgi varsa ATLAMA):
Soru: Ronaldo teknik direktoru kim?
Kaynaklar:
  1. "Ronaldo haberleri"
  2. "Ronaldo nun yeni teknik direktoru belli oldu - Postecoglou Al-Nassr"
Cevap: Cristiano Ronaldo'nun kulubu Al-Nassr'in teknik direktoru Ange Postecoglou'dur.

ORNEK 3 (gercekten yoksa):
Soru: X kisisi nerede yasiyor?
Kaynaklar: [X hakkinda bilgi var, yasadigi yer yok]
Cevap: X kisisi hakkinda bilgi bulundu ancak yasadigi yer kaynaklarda yer almamaktadir.


KULUP vs MILLI TAKIM (SON KURAL):
- Soru "X'in teknik direktoru" ise -> KULUP hocasi soruluyor
- Soru "X milli takim teknik direktoru" ise -> MILLI TAKIM hocasi
- Kaynakta iki isim varsa:
  * "Al-Nassr" yanindaki isim -> KULUP hocasi -> DOGRU CEVAP
  * "Portekiz" yanindaki isim -> MILLI TAKIM hocasi -> YANLIS
- Ornek: "Ronaldo nun yeni teknik direktoru belli oldu" basliginda
  KULUP hocasi yaziyor olabilir. Iceregini oku.

SON KONTROL (CEVAP YAZMADAN ONCE):
- Her "kim" sorusu icin TUM kaynaklari son kez kontrol et.
- Kaynak BASLIGI ilgili ise (ornek: "yeni teknik direktoru belli oldu"),
  ICERIGI OKU ve cevaba EKLE.
- Yarim isimler YAZMA (ornek: "Jorge..." yerine tam ismi bul).
- Kaynaklar arasinda CELISKI varsa (kulup vs milli takim),
  SORUYA EN UYGUN olani sec.

Simdi sen cevapla:"""


class ResearcherAgent(BaseAgent):
    """Web'de arastirir, coklu arama yapar, LLM ile ozetler."""

    def __init__(
        self,
        name: str,
        bus: Any,
        max_search_results: int = 5,
        use_llm_summary: bool = True,
    ) -> None:
        super().__init__(name, bus)
        self.max_search_results = max_search_results
        self.use_llm_summary = use_llm_summary
        self.llm = GroqLLMClient(model="openai/gpt-oss-120b") if use_llm_summary else None

    def _split_query(self, query: str) -> list[str]:
        """Soruyu alt sorulara boler VE her parcaya baglam ekler."""
        # Once virgul veya "ve" ile bol
        parts = []
        if "," in query:
            parts = [p.strip() for p in query.split(",") if p.strip()]
        elif " ve " in query.lower():
            parts = [p.strip() for p in re.split(r"\s+ve\s+", query, flags=re.IGNORECASE) if p.strip()]
        else:
            return [query]

        if len(parts) < 2:
            return [query]

        # Ana konuyu cikar: ilk parca genelde "X kimdir" -> "X"
        first = parts[0]
        # "kimdir", "nedir", "nerede" gibi kelimeleri cikar
        subject = first
        for kw in ["kimdir", "kim", "nedir", "ne demek", "nerede", "ne zaman"]:
            subject = re.sub(rf"\b{kw}\b", "", subject, flags=re.IGNORECASE)
        subject = subject.strip(" ?.,!")

        # Baglam ekle: ilk parca subject + sonraki parcalar
        enriched_parts = [first]
        for part in parts[1:]:
            # Eger parca cok kisa veya baglamsiz ise subject ekle
            if len(part.split()) < 4 and subject:
                enriched_parts.append(f"{subject} {part}")
            else:
                enriched_parts.append(part)

        return enriched_parts

    def _enrich_query(self, query: str) -> str:
        """Yil ekler (guncel bilgi icin)."""
        current_year = datetime.now().year
        if any(str(y) in query for y in range(current_year - 2, current_year + 2)):
            return query
        keywords = ["kim", "ne zaman", "guncel", "son", "yeni", "su an", "simdi"]
        if any(k in query.lower() for k in keywords):
            return f"{query} {current_year}"
        return query

    def _generate_followup_queries(self, query: str) -> list[str]:
        """Ilk aramada bulunamayan bilgiler icin alternatif sorgular uretir."""
        followups = []
        lower = query.lower()

        # Soru tipi: teknik direktor/hoca/coach
        if "teknik direkt" in lower or "hoca" in lower or "coach" in lower:
            # Kisi ismi cikar (Ronaldo, Messi, vs)
            # Buyuk harfle baslayan kelimeler
            words = query.split()
            subject_words = []
            for w in words:
                # Turkce karakter temizle
                clean = w.strip("?.,!").replace("'", "")
                if clean and clean[0].isupper() and len(clean) > 2:
                    if clean.lower() not in ["kim", "hoca", "teknik", "direktor", "direktoru", "nerede"]:
                        subject_words.append(clean)

            subject = " ".join(subject_words[:2]) if subject_words else ""

            # Kulupleri kontrol et
            clubs = ["al-nassr", "al nassr", "galatasaray", "fenerbahce", "besiktas", "real madrid", "barcelona", "manchester"]
            found_club = None
            for c in clubs:
                if c in lower:
                    found_club = c
                    break

            if found_club:
                # Kulup dogrudan yazilmis
                club_name = found_club.replace("al-nassr", "Al-Nassr").replace("al nassr", "Al-Nassr").title()
                followups.append(f"{found_club} new manager 2026")
                followups.append(f"{found_club} head coach 2026 who")
                followups.append(f"{found_club} teknik direktoru ismi")
                followups.append(f"{found_club} who is coach")
            elif subject:
                # Kisi isminden yola cik (Ronaldo -> Al-Nassr)
                followups.append(f"{subject} new manager 2026")
                followups.append(f"{subject} coach who 2026")
                followups.append(f"{subject} teknik direktoru ismi")
                followups.append(f"who is {subject} manager 2026")
            else:
                followups.append(f"{query} 2026 guncel")

        # "kim" + genel
        elif "kim" in lower or "kimdir" in lower:
            subject = re.sub(r"\b(kim|kimdir|nerede|ne zaman|hangi)\b", "", query, flags=re.IGNORECASE).strip(" ?.,!")
            followups.append(f"{subject} ismi nedir")
            followups.append(f"{subject} 2026 guncel")

        # Yerel yonetim
        elif "belediye" in lower or "vali" in lower:
            subject = re.sub(r"\b(kim|kimdir|nerede|hangi)\b", "", query, flags=re.IGNORECASE).strip(" ?.,!")
            followups.append(f"{subject} resmi aciklama 2026")
            followups.append(f"{subject} 2026 son dakika")

        return followups[:4]


    def _is_insufficient(self, answer: str) -> bool:
        """Cevap yetersiz mi? ('kaynakta yok' diyorsa True)."""
        # Turkce karakterleri ASCII'ye cevir
        tr_map = str.maketrans({
            "c": "c", "g": "g", "i": "i", "o": "o", "s": "s", "u": "u",
        })
        # Manuel replace (Türkçe karakterler)
        answer_ascii = answer.lower()
        answer_ascii = answer_ascii.replace("ç", "c").replace("ğ", "g")
        answer_ascii = answer_ascii.replace("ı", "i").replace("ö", "o")
        answer_ascii = answer_ascii.replace("ş", "s").replace("ü", "u")

        insufficient_phrases = [
            "kaynaklarda yer almamaktadir",
            "kaynaklarda yer almiyor",
            "bilgi bulunamadi",
            "kaynaklarda belirtilmemistir",
            "yer almamaktadir",
            "yer almiyor",
            "bulunmamaktadir",
            "bulunmuyor",
            "bilgisi kaynaklarda",
            "isim kaynaklarda",
            "kaynakta yok",
            "bilgi yok",
            "bilinmiyor",
            "bilgi yer almamaktadir",
            "yer almamistir",
        ]
        return any(phrase in answer_ascii for phrase in insufficient_phrases)


    def _summarize_with_llm(self, query: str, sources: list) -> str:
        """Kaynaklari LLM ile ozetler. Kaynaklari alakaya gore siralar."""
        if not self.llm or not sources:
            return ""

        # Soru kelimeleri (alaka puanlamasi icin)
        query_words = set(re.findall(r"\w+", query.lower()))

        # Alakasiz kelimeler
        stop = {"kim", "kimdir", "nerede", "ne", "zaman", "hangi", "kac",
                "ve", "mi", "mu", "midir", "mudur", "the", "bir"}

        def relevance(s):
            """Kaynak alakasini puanla (0-100)."""
            text = (s['title'] + " " + s['snippet']).lower()
            score = 0
            for w in query_words:
                if w in stop or len(w) < 3:
                    continue
                if w in text:
                    score += 10
            # Baslik eslesmesi ekstra puan
            for w in query_words:
                if w in stop or len(w) < 3:
                    continue
                if w in s['title'].lower():
                    score += 15
            return score

        # Kaynaklari alakaya gore sirala
        ranked = sorted(sources, key=relevance, reverse=True)

        # Ilk 5 kaynagi al (daha fazla olursa LLM kaybolur)
        top = ranked[:6]

        context_lines = []
        for i, s in enumerate(top, 1):
            context_lines.append(f"[KAYNAK {i}]")
            context_lines.append(f"Baslik: {s['title']}")
            context_lines.append(f"Icerik: {s['snippet'][:1500]}")
            context_lines.append(f"URL: {s['url'][:100]}")
            context_lines.append("")

        context = "\n".join(context_lines)
        prompt = f"Soru: {query}\n\n{context}\n\nCevap (max 4 cumle):"
        try:
            answer = self.llm.chat(prompt=prompt, system=SUMMARY_PROMPT)
            return answer.strip()
        except Exception as e:
            logger.exception("researcher.summary_failed", error=str(e))
            return ""

    def _collect_sources(self, query: str) -> tuple[list[dict], int]:
        """Tek veya coklu arama yapar, kaynaklari doner."""
        sub_queries = self._split_query(query)
        all_sources = []

        if len(sub_queries) > 1:
            logger.info("researcher.multi_search", count=len(sub_queries), queries=sub_queries)
            # Her alt soru icin ayri arama
            for sq in sub_queries:
                enriched = self._enrich_query(sq)
                found = search(enriched, max_results=3)
                all_sources.extend(found)
        else:
            enriched = self._enrich_query(query)
            all_sources = search(enriched, max_results=self.max_search_results)

        # Tekrarlari temizle (URL bazli)
        seen_urls = set()
        unique_sources = []
        for s in all_sources:
            if s["url"] not in seen_urls:
                seen_urls.add(s["url"])
                unique_sources.append(s)

        # Max 8 kaynak
        return unique_sources[:8], len(sub_queries)

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return

        query = str(message.content)
        logger.info("researcher.start", query=query[:80])

        try:
            sources, sub_count = self._collect_sources(query)

            if not sources:
                answer = "Bu konuda web'de guvenilir bir sonuc bulunamadi."
            else:
                summary = self._summarize_with_llm(query, sources)
                if summary:
                    answer = summary
                else:
                    today = datetime.now().strftime("%Y-%m-%d")
                    lines = [f"{today} itibariyle web arama sonuclari:", f"Sorgu: {query}", ""]
                    for i, s in enumerate(sources, 1):
                        lines.append(f"{i}. {s['title']}")
                        lines.append(f"   {s['snippet']}")
                        lines.append("")
                    answer = "\n".join(lines)

                # FOLLOW-UP: Cevap yetersizse farkli sorguyla tekrar ara
                if self._is_insufficient(answer):
                    logger.info("researcher.followup_needed", query=query[:60])
                    followups = self._generate_followup_queries(query)
                    logger.info("researcher.followup_queries", queries=followups)

                    extra_sources = []
                    for fq in followups:
                        found = search(fq, max_results=3)
                        extra_sources.extend(found)

                    # Tekrarlari temizle
                    seen_urls = {s["url"] for s in sources}
                    new_sources = [s for s in extra_sources if s["url"] not in seen_urls]

                    if new_sources:
                        logger.info("researcher.followup_found", new_count=len(new_sources))
                        # Yeni kaynaklarla tekrar ozetle
                        all_sources = sources + new_sources
                        summary2 = self._summarize_with_llm(query, all_sources)
                        if summary2:
                            answer = summary2
                            sources = all_sources
                            logger.info("researcher.followup_success")

            await self.send(
                message.sender,
                {
                    "answer": answer,
                    "research": answer,
                    "sources": [{"title": s["title"], "url": s["url"]} for s in sources],
                    "query": query,
                    "source_count": len(sources),
                    "summarized": bool(self.llm and sources),
                    "multi_search": sub_count > 1,
                },
                msg_type="result",
            )
            logger.info("researcher.done", sources=len(sources), multi_search=sub_count > 1)

        except Exception as e:
            logger.exception("researcher.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def __repr__(self) -> str:
        return f"<ResearcherAgent name={self.name!r} (multi-search, llm-summary)>"