from tools.web_search import search

test_queries = [
    "2026 Dunya Kupasi sampiyonu kim?",
    "Python nedir?",
    "2024 Nobel Odulu kime verildi?",
]

for q in test_queries:
    print(f"\n=== {q} ===")
    results = search(q, max_results=3)
    print(f"Sonuc sayisi: {len(results)}")
    for r in results:
        print(f"  - {r['title']}")
        print(f"    {r['snippet'][:100]}")