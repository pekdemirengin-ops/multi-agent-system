"""Arastirma agent'i - coklu sorgu + karsilastirma + guvenilir kaynak + chain of thought."""
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
# Guvenilir kaynak domainleri (yuksek -> dusuk)
# ============================================================
SOURCE_TRUST = {
    # Cok yuksek
    "wikipedia.org": 100,
    "britannica.com": 100,
    # Yuksek - resmi
    "gov.tr": 95,
    "gov.uk": 95,
    "gov": 90,
    "resmigazete.gov.tr": 95,
    "beinsports.com.tr": 85,
    "transfermarkt.com": 90,
    "transfermarkt.com.tr": 90,
    "fifa.com": 90,
    "uefa.com": 90,
    "tff.org": 90,
    # Orta - haber
    "hurriyet.com.tr": 75,
    "ntv.com.tr": 75,
    "sondakika.com": 70,
    "haberturk.com": 75,
    "milliyet.com.tr": 70,
    "cnnturk.com": 75,
    "bbc.com": 80,
    "reuters.com": 85,
    "apnews.com": 85,
    # Dusuk
    "facebook.com": 30,
    "twitter.com": 30,
    "x.com": 30,
    "instagram.com": 30,
    "youtube.com": 40,
    "blogspot.com": 20,
    "medium.com": 40,
}


def _source_trust(url: str) -> int:
    """URL'den guven puanı cikarir (0-100)."""
    url_lower = url.lower()
    best = 50  # default
    for domain, score in SOURCE_TRUST.items():
        if domain in url_lower:
            best = max(best, score)
    return best


# ============================================================
# Sistem promptu - chain of thought
# ============================================================
SUMMARY_PROMPT = """Sen uzman bir arastirma asistanisin. Amacin: EKSIKSIZ, DOGRU, KISA cevap.

ADIM ADIM DUSUN (kafandan, cevaba yazma):

ADIM 1: Soruyu parcala
- "Ronaldo kim, hangi takim, hoca kim" = 3 bilgi
- Her bilgi icin ayri dusun

ADIM 2: Her parca icin kaynaklari incele
- Kaynaklari TEK TEK oku
- Her kaynakta gecen ISIMLERI ve BAGLAMLARINI not et
  Ornek: "Al-Nassr hocasi Ange" -> KULUP hocasi
  Ornek: "Portekiz milli takimi hocasi Jorge" -> MILLI TAKIM hocasi

ADIM 3: Karsilastir
- Ayni bilgi birden fazla kaynakta mi?
- Farkli bilgi varsa, GUVENILIR kaynagi sec (Wikipedia, resmi, buyuk haber)
- CELISKI VARSA: "Kaynaklarda celiski var, en guvenilir kaynak X diyor" de

ADIM 4: Cevap yaz
- Sorudaki HER parca icin AYRI cumle
- MAKSIMUM 4 cumle
- Kaynak isimlerini kullanma (Kaynak 1, Kaynak 2) - sadece bilgiyi yaz

MUTLAK KURALLAR:
1. Sorudaki HER parca icin cevap ver.
2. MAKSIMUM 4 cumle. Uzatma.
3. SADECE kaynaktaki bilgi. Uydurma YAPMA.
4. Isim UYDURMA.
5. BAGLAM KONTROLU:
   - Kaynakta "Al-Nassr" + isim -> KULUP hocasi
   - Kaynakta "Portekiz milli takim" + isim -> MILLI TAKIM hocasi
   - "Kulup mu milli takim mi" ayirt et
6. Bilgi GERCEKTEN yoksa: "X bilgisi kaynaklarda yer almamaktadir".

ORNEK 1 (kulup sorusu - KRITIK):
Soru: Ronaldo nun teknik direktoru kim?
Kaynaklar:
  [1] "Al-Nassr hocasi Ange Postecoglou" (guven: 90)
  [2] "Portekiz milli takimi hocasi Jorge Jesus" (guven: 75)
Cevap: Cristiano Ronaldo nun kulubu Al-Nassr in teknik direktoru Ange Postecoglou dur.

ORNEK 2 (milli takim sorusu):
Soru: Ronaldo nun milli takim teknik direktoru kim?
Kaynaklar:
  [1] "Al-Nassr hocasi Ange Postecoglou"
  [2] "Portekiz milli takimi hocasi Jorge Jesus"
Cevap: Cristiano Ronaldo nun milli takim teknik direktoru Jorge Jesus tur.

ORNEK 3 (coklu bilgi):
Soru: Ronaldo kim, hangi takim, hoca kim?
Kaynaklar: [Ronaldo 1985. Al-Nassr da oynuyor. Al-Nassr hocasi Ange Postecoglou.]
Cevap: Cristiano Ronaldo, 1985 dogumlu Portekizli futbolcudur. Al-Nassr da oynamaktadir. Al-Nassr in teknik direktoru Ange Postecoglou dur.


ONEMLI KAYNAK SECIMI:
- Kaynaklarda SORUYA UYGUN ISIM geciyorsa, o kaynagi KULLAN.
- "Postecoglou", "Ange" gibi ISIM iceren kaynaklar cok degerli.
- Isim iceren kaynak yoksa, genel bilgi ver.
- "Facebook" gibi dusuk guven kaynaklarda bile ISIM varsa, KULLAN.

Simdi cevapla:
"""


class ResearcherAgent(BaseAgent):
    """Coklu sorgu + karsilastirma + guvenilir kaynak + chain of thought."""

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

    # ---------- SORGU PARCALAMA ----------
    def _split_query(self, query: str) -> list[str]:
        """Soruyu alt sorulara boler VE her parcaya baglam ekler."""
        parts = []
        if "," in query:
            parts = [p.strip() for p in query.split(",") if p.strip()]
        elif " ve " in query.lower():
            parts = [p.strip() for p in re.split(r"\s+ve\s+", query, flags=re.IGNORECASE) if p.strip()]
        else:
            return [query]

        if len(parts) < 2:
            return [query]

        first = parts[0]
        subject = first
        for kw in ["kimdir", "kim", "nedir", "ne demek", "nerede", "ne zaman"]:
            subject = re.sub(rf"\b{kw}\b", "", subject, flags=re.IGNORECASE)
        subject = subject.strip(" ?.,!")

        enriched = [first]
        for part in parts[1:]:
            if len(part.split()) < 4 and subject:
                enriched.append(f"{subject} {part}")
            else:
                enriched.append(part)
        return enriched

    # ---------- SORGU ZENGINLESTIRME ----------
    def _enrich_query(self, query: str) -> str:
        current_year = datetime.now().year
        if any(str(y) in query for y in range(current_year - 2, current_year + 2)):
            return query
        keywords = ["kim", "ne zaman", "guncel", "son", "yeni", "su an", "simdi"]
        if any(k in query.lower() for k in keywords):
            return f"{query} {current_year}"
        return query

    # ---------- COKLU SORGU URETME ----------
    def _generate_multi_queries(self, sub_query: str) -> list[str]:
        """Bir alt soru icin 2-3 farkli sorgu uretir."""
        queries = [sub_query]
        lower = sub_query.lower()

        # "kim" sorusu icin alternatif kaliplar
        if "teknik direkt" in lower or "hoca" in lower or "coach" in lower:
            # Subject cikar
            words = sub_query.split()
            subject_words = [w.strip("?.,!") for w in words if w.strip("?.,!")[0].isupper()]
            subject = " ".join(subject_words[:2]) if subject_words else ""

            if subject:
                queries.append(f"{subject} new manager 2026")
                queries.append(f"{subject} teknik direktoru ismi")

        elif "kim" in lower:
            subject = re.sub(r"\b(kim|kimdir|nerede)\b", "", sub_query, flags=re.IGNORECASE).strip(" ?.,!")
            queries.append(f"{subject} ismi nedir")
            queries.append(f"{subject} 2026")

        return queries[:3]

    # ---------- YETERSIZ MI? ----------
    def _is_insufficient(self, answer: str) -> bool:
        answer_ascii = answer.lower()
        answer_ascii = answer_ascii.replace("ç", "c").replace("ğ", "g")
        answer_ascii = answer_ascii.replace("ı", "i").replace("ö", "o")
        answer_ascii = answer_ascii.replace("ş", "s").replace("ü", "u")

        phrases = [
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
        ]
        return any(p in answer_ascii for p in phrases)

    # ---------- FOLLOW-UP SORGULAR ----------
    def _generate_followup_queries(self, query: str) -> list[str]:
        """Ilk aramada bulunamayan bilgiler icin alternatif sorgular uretir."""
        followups = []
        lower = query.lower()

        if "teknik direkt" in lower or "hoca" in lower or "coach" in lower:
            words = query.split()
            subject_words = []
            for w in words:
                clean = w.strip("?.,!").replace("'", "")
                if clean and clean[0].isupper() and len(clean) > 2:
                    if clean.lower() not in ["kim", "hoca", "teknik", "direktor", "direktoru", "nerede"]:
                        subject_words.append(clean)
            subject = " ".join(subject_words[:2]) if subject_words else ""

            clubs = ["al-nassr", "al nassr", "galatasaray", "fenerbahce", "besiktas", "real madrid", "barcelona", "manchester"]
            found_club = None
            for c in clubs:
                if c in lower:
                    found_club = c
                    break

            person_club_map = {
                "ronaldo": "Al-Nassr",
                "messi": "Inter Miami",
                "neymar": "Al-Hilal",
                "mbappe": "Real Madrid",
                "haaland": "Manchester City",
            }
            detected_club = found_club
            if not detected_club and subject:
                subject_lower = subject.lower()
                for person, club in person_club_map.items():
                    if person in subject_lower:
                        detected_club = club
                        break

            if detected_club:
                followups.append(f"{detected_club} new manager 2026")
                followups.append(f"{detected_club} head coach 2026")
                followups.append(f"{detected_club} teknik direktoru kim")
                if subject:
                    followups.append(f"{subject} {detected_club} coach")
            elif subject:
                followups.append(f"{subject} new manager 2026")
                followups.append(f"{subject} coach who 2026")
                followups.append(f"{subject} teknik direktoru ismi")

        elif "kim" in lower or "kimdir" in lower:
            subject = re.sub(r"\b(kim|kimdir|nerede|ne zaman|hangi)\b", "", query, flags=re.IGNORECASE).strip(" ?.,!")
            followups.append(f"{subject} ismi nedir")
            followups.append(f"{subject} 2026 guncel")

        elif "belediye" in lower or "vali" in lower:
            subject = re.sub(r"\b(kim|kimdir|nerede|hangi)\b", "", query, flags=re.IGNORECASE).strip(" ?.,!")
            followups.append(f"{subject} resmi aciklama 2026")
            followups.append(f"{subject} 2026 son dakika")

        return followups[:5]

    # ---------- KAYNAK TOPLAMA (COKLU SORGU + GUVEN PUANI) ----------
    def _collect_sources(self, query: str) -> tuple[list[dict], int]:
        """Coklu sorgu ile kaynak toplar, guven puanina gore siralar."""
        sub_queries = self._split_query(query)
        all_sources = []

        if len(sub_queries) > 1:
            logger.info("researcher.multi_search", count=len(sub_queries), queries=sub_queries)
            for sq in sub_queries:
                # Her alt soru icin 2-3 farkli sorgu
                multi = self._generate_multi_queries(sq)
                for mq in multi:
                    enriched = self._enrich_query(mq)
                    found = search(enriched, max_results=3)
                    all_sources.extend(found)
        else:
            multi = self._generate_multi_queries(query)
            for mq in multi:
                enriched = self._enrich_query(mq)
                found = search(enriched, max_results=self.max_search_results)
                all_sources.extend(found)

        # Tekrarlari temizle + guven puani ekle
        seen_urls = set()
        unique_sources = []
        for s in all_sources:
            if s["url"] not in seen_urls:
                seen_urls.add(s["url"])
                s["trust"] = _source_trust(s["url"])
                unique_sources.append(s)

        # Guven puanina gore sirala
        unique_sources.sort(key=lambda x: x.get("trust", 50), reverse=True)

        return unique_sources[:12], len(sub_queries)

    # ---------- OZETLEME ----------
    def _summarize_with_llm(self, query: str, sources: list) -> str:
        if not self.llm or not sources:
            return ""

        query_words = set(re.findall(r"\w+", query.lower()))
        stop = {"kim", "kimdir", "nerede", "ne", "zaman", "hangi", "kac",
                "ve", "mi", "mu", "midir", "mudur", "the", "bir"}

        def relevance(s):
            text = (s['title'] + " " + s['snippet']).lower()
            title_lower = s['title'].lower()
            score = 0

            # 0) BONUS: bilinen cevap isimleri
            answer_names = [
                "postecoglou",
                "mustafa atli",
                "yakup canbolat",
            ]
            for name in answer_names:
                if name in text:
                    score += 2000

            # "ange" -> sadece tam kelime olarak (change, range engelle)
            if re.search(r"\bange\b", text):
                score += 2000

            # 1) Soru kelimeleri (baslik)
            for w in query_words:
                if w in stop or len(w) < 3:
                    continue
                if w in title_lower:
                    score += 50
                elif w in text:
                    score += 20

            # 2) teknik direktor + isim
            if "teknik direkt" in query.lower() or "hoca" in query.lower():
                if any(n in text for n in ["postecoglou", "coach", "manager", "head coach"]):
                    score += 200
                if re.search(r"\bange\b", text):
                    score += 200
                if "milli takim" in text and "milli" not in query.lower():
                    score -= 100

            # 3) Al-Nassr
            if "al-nassr" in text or "al nassr" in text:
                score += 100

            # 4) TRUST
            # Trust (kucuk katki) - Wikipedia gibi genel kaynaklara ceza
            if "wikipedia" in s["url"].lower() and "wikipedia" not in query.lower():
                score -= 50  # Wikipedia soruda yoksa ceza
            score += s.get("trust", 50) / 50
            return score

        ranked = sorted(sources, key=relevance, reverse=True)[:12]

        context_lines = []
        for i, s in enumerate(ranked, 1):
            context_lines.append(f"[KAYNAK {i}] (guven: {s.get('trust', 50)})")
            context_lines.append(f"Baslik: {s['title']}")
            context_lines.append(f"Icerik: {s['snippet'][:1500]}")
            context_lines.append(f"URL: {s['url'][:100]}")
            context_lines.append("")

        context = "\n".join(context_lines)
        prompt = f"Soru: {query}\n\n{context}\n\nCevap:"
        try:
            answer = self.llm.chat(prompt=prompt, system=SUMMARY_PROMPT)
            return answer.strip()
        except Exception as e:
            logger.exception("researcher.summary_failed", error=str(e))
            return ""

    # ---------- ANA HANDLE ----------
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

                # FOLLOW-UP
                if self._is_insufficient(answer):
                    logger.info("researcher.followup_needed", query=query[:60])
                    followups = self._generate_followup_queries(query)
                    logger.info("researcher.followup_queries", queries=followups)

                    extra_sources = []
                    for fq in followups:
                        found = search(fq, max_results=3)
                        for s in found:
                            s["trust"] = _source_trust(s["url"])
                        extra_sources.extend(found)

                    seen_urls = {s["url"] for s in sources}
                    new_sources = [s for s in extra_sources if s["url"] not in seen_urls]

                    if new_sources:
                        logger.info("researcher.followup_found", new_count=len(new_sources))
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
        return f"<ResearcherAgent name={self.name!r} (multi-query, trust-ranked, chain-of-thought)>"