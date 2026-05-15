from modules.news_fetcher import fetch_news_headlines
from modules.news_verifier import verify_headline

subjects = [
    'Data Analytics',
    'Power BI',
    'Artificial Intelligence',
    'Machine Learning',
    'SQL',
    'Data Visualization',
    'Use of AI in Data Analytics',
]

total_pass = 0
total_fail = 0

for subject in subjects:
    headlines = fetch_news_headlines(subject)
    print(f"\n--- {subject} ({len(headlines)} headlines) ---")
    for h in headlines[:5]:
        title = h.get('title', '')
        if not title:
            continue
        result = verify_headline(title, subject)
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {title[:90]}")
        if result:
            total_pass += 1
        else:
            total_fail += 1

print(f"\n{'='*50}")
print(f"TOTAL PASS: {total_pass}")
print(f"TOTAL FAIL: {total_fail}")
print(f"PASS RATE : {round(total_pass/(total_pass+total_fail)*100) if total_pass+total_fail > 0 else 0}%")
