from tools.web_search import search

results = search("Fenerbahce baskani kim?", max_results=5)
print(f"Sonuc: {len(results)}")
print()

for i, r in enumerate(results, 1):
    print(f"{i}. {r['title']}")
    print(f"   {r['snippet'][:150]}")
    print()