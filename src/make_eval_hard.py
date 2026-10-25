import json
import os

rows = {r["id"]: r for r in map(json.loads, open("data/processed/chunks.jsonl", encoding="utf-8"))}
E, P, C = "employment_act", "pdpa", "contracts_act"

# Hard = real-life scenarios, indirect wording, answer not named in the question.
# (question, gold section ids [any one counts], keywords that must appear in the gold text)
HARD = [
 ("My boss fired me yesterday with no warning after three years. Was that allowed?", [f"{E}-12", f"{E}-13"], ["notice"]),
 ("I'm expecting a baby. Can my company let me go because of it?", [f"{E}-41A", f"{E}-42"], ["pregnant"]),
 ("My salary was cut for a loan I never took. Is that legal?", [f"{E}-24"], ["deduction"]),
 ("Do I have to work on public holidays?", [f"{E}-60D"], ["holiday"]),
 ("My manager keeps making sexual comments at me. What must the company do about it?", [f"{E}-81B", f"{E}-81C", f"{E}-81H"], ["sexual harassment"]),
 ("Can I ask to work from home or change my hours?", [f"{E}-60P", f"{E}-60Q"], ["flexible working"]),
 ("If a company goes bust, who gets paid first, the bank or the workers?", [f"{E}-31"], ["wages"]),
 ("How soon after I quit must I get my final salary?", [f"{E}-20"], ["wages"]),
 ("A shop keeps asking for my IC number to give me loyalty points. Do they need my permission?", [f"{P}-6", f"{P}-7"], ["consent"]),
 ("A company leaked my details to a telemarketer. Who do I report it to?", [f"{P}-104"], ["complaint"]),
 ("Can my bank pass my information to its head office overseas?", [f"{P}-129"], ["outside Malaysia"]),
 ("How long must a company keep customer records before deleting them?", [f"{P}-10"], ["kept longer"]),
 ("I asked a company for my data and they ignored me. Is that allowed?", [f"{P}-31", f"{P}-32"], ["data access request"]),
 ("Is information about my health or religion treated more strictly?", [f"{P}-40", f"{P}-4"], ["sensitive personal data"]),
 ("Is it a crime to sell people's personal data without permission?", [f"{P}-130"], ["personal data"]),
 ("Hackers stole customer data from a firm. What protection duty did the firm have?", [f"{P}-9"], ["security"]),
 ("My landlord threatened to call the police unless I signed. Can I cancel the agreement?", [f"{C}-15", f"{C}-19"], ["coercion"]),
 ("A 16-year-old signed a car purchase agreement. Is it binding?", [f"{C}-11"], ["majority"]),
 ("I promised to repay my friend but he gave nothing in return. Is my promise enforceable?", [f"{C}-26", f"{C}-10"], ["consideration"]),
 ("I signed a deal saying I can never work in my industry again. Is that valid?", [f"{C}-28"], ["restrained"]),
 ("I lent my laptop to a colleague and he broke it. Who pays?", [f"{C}-104", f"{C}-105"], ["bailee"]),
 ("A friend guaranteed my loan and the bank changed the terms without telling him. Is he still liable?", [f"{C}-86"], ["surety"]),
 ("My agent made a deal beyond what I allowed him to do. Am I bound by it?", [f"{C}-180", f"{C}-181"], ["agent"]),
 ("A seller lied about the car's condition. Can I cancel the deal?", [f"{C}-19", f"{C}-17", f"{C}-18"], ["misrepresentation"]),
 ("I bet money on a football match with a friend. Can he sue me if I don't pay?", [f"{C}-31"], ["wager"]),
 ("The supplier delivered late but I accepted the goods. Can I still claim damages?", [f"{C}-56"], ["time"]),
 ("My contract says I pay a fixed penalty if I leave early. Is that enforceable?", [f"{C}-75"], ["penalty"]),
 ("What if both of us were mistaken about what we were buying?", [f"{C}-21"], ["mistake"]),
]

bad = 0
new = []
for i, (q, gold, kws) in enumerate(HARD, 1):
    for g in gold:
        if g not in rows:
            print("MISSING SECTION", i, g)
            bad += 1
    text = " ".join(rows[g]["text"] for g in gold if g in rows).lower()
    for kw in kws:
        if kw.lower() not in text:
            print("KEYWORD MISS", i, q[:50], "|", kw, "|", gold)
            bad += 1
    new.append({"id": f"h{i:03d}", "question": q, "gold": gold, "answerable": True, "split": "hard"})

old = [json.loads(l) for l in open("eval/questions.jsonl", encoding="utf-8")]
old = [r for r in old if r.get("split") != "hard"]  # safe to rerun
for r in old:
    r.setdefault("split", "easy")

os.makedirs("eval", exist_ok=True)
with open("eval/questions.jsonl", "w", encoding="utf-8") as f:
    for r in old + new:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"hard questions: {len(new)}, problems: {bad}, total in file: {len(old) + len(new)}")