from core.pipeline import list_pipelines

print("=== Kayitli Pipeline'lar ===")
for p in list_pipelines():
    print(f"  {p['name']}: {'  '.join(p['steps'])}")
