import json
import os

rows = {r["id"]: r for r in map(json.loads, open("data/processed/chunks.jsonl", encoding="utf-8"))}

E, P, C = "employment_act", "pdpa", "contracts_act"
# (question, gold section ids, keywords that must appear in the gold text)
Q = [
 # Employment Act
 ("How many days of paid annual leave does an employee get after more than five years of service?", [f"{E}-60E"], ["sixteen days"]),
 ("How long is maternity leave?", [f"{E}-37"], ["ninety"]),
 ("How many paid public holidays is an employee entitled to each year?", [f"{E}-60D"], ["eleven"]),
 ("What is the maximum number of working hours in a week?", [f"{E}-60A"], ["hours"]),
 ("How much notice must an employer give to terminate a contract of service?", [f"{E}-12"], ["notice"]),
 ("Can an employer dismiss an employee without notice for misconduct?", [f"{E}-14"], ["misconduct"]),
 ("By when must wages be paid after the end of the wage period?", [f"{E}-19"], ["seventh day"]),
 ("What deductions is an employer allowed to make from an employee's wages?", [f"{E}-24"], ["deduction"]),
 ("How many days of paid sick leave is an employee entitled to?", [f"{E}-60F"], ["sick leave"]),
 ("Can an employer terminate a pregnant employee?", [f"{E}-41A"], ["pregnant"]),
 ("What must an employer pay if an employee works on a rest day?", [f"{E}-60"], ["rest day"]),
 ("What is the overtime rate of pay?", [f"{E}-60A"], ["overtime"]),
 ("What should I do if I am sexually harassed at work?", [f"{E}-81B", f"{E}-81D"], ["sexual harassment"]),
 ("Can an employee request flexible working arrangements?", [f"{E}-60P", f"{E}-60Q"], ["flexible working"]),
 ("What is the punishment for forcing someone to work against their will?", [f"{E}-90B"], ["forces an employee"]),
 ("Where do I complain if my employer does not pay my wages?", [f"{E}-69"], ["Director General"]),
 ("Must a contract of service be in writing?", [f"{E}-10"], ["writing"]),
 ("What benefits must an employer pay if terminating an employee because of redundancy?", [f"{E}-60J"], ["lay-off"]),
 # PDPA
 ("What are the personal data protection principles?", [f"{P}-5"], ["Principle"]),
 ("Can my personal data be disclosed to others without my consent?", [f"{P}-8", f"{P}-39"], ["consent"]),
 ("How do I ask a company for a copy of my personal data?", [f"{P}-30", f"{P}-31"], ["access"]),
 ("Can I ask a company to correct my personal data?", [f"{P}-34"], ["correct"]),
 ("What counts as sensitive personal data?", [f"{P}-4"], ["sensitive personal data"]),
 ("Can a company send my personal data to another country?", [f"{P}-129"], ["outside Malaysia"]),
 ("How long can a company keep my personal data?", [f"{P}-10"], ["kept longer"]),
 ("What security steps must a company take to protect personal data?", [f"{P}-9"], ["security"]),
 ("How do I file a complaint about misuse of my personal data?", [f"{P}-104"], ["complaint"]),
 ("What is the penalty for unlawfully collecting or selling personal data?", [f"{P}-130"], ["personal data"]),
 ("Can I withdraw my consent for a company to process my data?", [f"{P}-38"], ["withdraw"]),
 ("Which organisations must register as data users?", [f"{P}-14"], ["register"]),
 ("Does the personal data law apply to the government?", [f"{P}-3"], ["Federal Government"]),
 ("Can I stop a company from using my data for direct marketing?", [f"{P}-43"], ["direct marketing"]),
 ("What does the Personal Data Protection Commissioner do?", [f"{P}-48"], ["Commissioner"]),
 # Contracts Act
 ("What is coercion under contract law?", [f"{C}-15"], ["Coercion"]),
 ("What is undue influence?", [f"{C}-16"], ["undue influence"]),
 ("What is a contract of guarantee?", [f"{C}-79"], ["guarantee"]),
 ("When is an agreement void because it restrains someone's trade or profession?", [f"{C}-28"], ["restrained"]),
 ("Who is competent to enter into a contract?", [f"{C}-11"], ["sound mind"]),
 ("Until when can a proposal be revoked?", [f"{C}-5"], ["revoked"]),
 ("What compensation can I claim if the other party breaks the contract?", [f"{C}-74"], ["compensation"]),
 ("What is a contract of indemnity?", [f"{C}-77"], ["indemnity"]),
 ("Is an agreement without consideration valid?", [f"{C}-26"], ["consideration"]),
 ("What duty of care does a bailee owe?", [f"{C}-104"], ["care"]),
 ("What is a pledge and who is a pawnee?", [f"{C}-125"], ["pledge"]),
 ("When does an agent's authority come to an end?", [f"{C}-154"], ["terminated"]),
 ("What happens if a contract becomes impossible to perform?", [f"{C}-57"], ["impossible"]),
 ("What must an agent do when conducting the principal's business?", [f"{C}-164"], ["agent"]),
 ("Are wagering agreements enforceable?", [f"{C}-31"], ["wager"]),
 ("What is novation of a contract?", [f"{C}-63"], ["substitute a new contract"]),
 ("What is a contingent contract?", [f"{C}-32"], ["contingent"]),
 ("Is a contract voidable if consent was obtained by fraud?", [f"{C}-19"], ["fraud"]),
]
OOS = [
 "What is the minimum wage in Malaysia?",
 "How do I register a new company in Malaysia?",
 "What is the punishment for theft?",
 "How long does a divorce take in Malaysia?",
 "Can I sue someone for defamation?",
 "What is the income tax rate for individuals?",
]

bad = 0
out = []
for i, (q, gold, kws) in enumerate(Q, 1):
    for g in gold:
        if g not in rows:
            print("MISSING SECTION", i, g)
            bad += 1
    text = " ".join(rows[g]["text"] for g in gold if g in rows).lower()
    for kw in kws:
        if kw.lower() not in text:
            print("KEYWORD MISS", i, q[:50], "|", kw, "|", gold)
            bad += 1
    out.append({"id": f"q{i:03d}", "question": q, "gold": gold, "answerable": True})
for j, q in enumerate(OOS, len(Q) + 1):
    out.append({"id": f"q{j:03d}", "question": q, "gold": [], "answerable": False})

os.makedirs("eval", exist_ok=True)
print("questions:", len(out), "answerable:", len(Q), "problems:", bad)
with open("eval/questions.jsonl", "w", encoding="utf-8") as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")