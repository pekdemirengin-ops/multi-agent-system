import asyncio
from skills import skill_registry, CalculatorSkill, TranslationSkill, FileOperationsSkill

async def test():
    print("=== Kayitli skill'ler ===")
    print(skill_registry.list_skills())
    print()

    # Calculator
    print("=== Calculator ===")
    calc = CalculatorSkill()
    r = await calc(expression="2 + 3 * 4")
    print(f"2 + 3 * 4 = {r.get('result')}")

    r = await calc(expression="sqrt(16) + 10")
    print(f"sqrt(16) + 10 = {r.get('result')}")

    r = await calc(expression="2^10")
    print(f"2^10 = {r.get('result')}")

    # Translation
    print()
    print("=== Translation ===")
    trans = TranslationSkill()
    r = await trans(text="Merhaba, nasilsin?", target_lang="en")
    print(f"TR->EN: {r.get('translation', '')[:100]}")

    # File Operations
    print()
    print("=== File Operations ===")
    file_skill = FileOperationsSkill()
    r = await file_skill(action="write", path="test.txt", content="Merhaba dunya")
    print(f"Yaz: {r}")

    r = await file_skill(action="read", path="test.txt")
    print(f"Oku: {r.get('content', '')}")

asyncio.run(test())
