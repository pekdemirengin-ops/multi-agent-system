from tools.web_search import search

# Daha spesifik aramalar
queries = [
    "Fenerbahce baskani 2026 Aziz Yildirim",
    "Fenerbahce yeni baskani secildi 2026",
    "Aziz Yildirim Fenerbahce baskani 2026",
]

for q in queries:
    print(f"\n{'='*60}")
    print(f"Sorgu: {q}")
    print('='*60)
    results = search(q, max_results=3)
    for i, r in enumerate(results, 1):
        print(f"{i}. {r['title']}")
        print(f"   {r['snippet'][:200]}")
        print()