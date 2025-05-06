import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
import os
import html

base_url = "https://www.talentd.in/jobs?page="
headers = {
    "User-Agent": "Mozilla/5.0"
}

# Detect total pages
first_page = requests.get(base_url + "1", headers=headers)
soup = BeautifulSoup(first_page.text, "html.parser")
pagination = soup.select("div.hidden.sm\\:flex a[href*='page=']")
last_page = max([int(a.text.strip()) for a in pagination if a.text.strip().isdigit()] or [1])
print(f"📄 Total pages detected: {last_page}")

jobs_data = []

def clean_salary(salary):
    if not salary:
        return ""
    salary = salary.replace("\u20b9", "INR").replace("₹", "INR").replace("?", "INR")
    return salary.strip()

for page in range(1, last_page + 1):
    print(f"🔍 Scraping page {page}...")
    response = requests.get(base_url + str(page), headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to fetch page {page}")
        continue

    soup = BeautifulSoup(response.text, "html.parser")
    job_cards = soup.find_all("div", class_="!bg-white/80 backdrop-blur-sm rounded-xl border border-gray-200/50 p-4 hover:shadow-lg transition-all hover:border-blue-200/50")

    for job in job_cards:
        def clean(text):
            return html.unescape(text.strip()) if text else ""

        title = clean(job.select_one("h2.text-lg").text) if job.select_one("h2.text-lg") else ""
        company_location = clean(job.select_one("p.text-gray-600").text) if job.select_one("p.text-gray-600") else ""
        salary_raw = clean(job.select_one("p.text-green-600").text) if job.select_one("p.text-green-600") else ""
        salary = clean_salary(salary_raw)
        posted_date = clean(job.select_one("p.text-gray-500").text) if job.select_one("p.text-gray-500") else ""

        tags = job.select("div.mt-2 span.text-sm")
        years = clean(tags[0].text) if len(tags) > 0 else ""
        job_type = clean(tags[1].text) if len(tags) > 1 else ""

        skills_list = [clean(s.text) for s in job.select("div.flex-wrap.gap-2.mt-3 span")]
        skills = ", ".join(skills_list)

        apply_button = job.select_one("a.bg-blue-600")
        apply_url = urljoin(base_url, apply_button["href"]) if apply_button and "href" in apply_button.attrs else ""

        img_tag = job.select_one("img.rounded-lg")
        logo_url = urljoin(base_url, img_tag["src"]) if img_tag and "src" in img_tag.attrs else ""

        job_entry = {
            "Job Title": title,
            "Company & Location": company_location,
            "Salary": salary,
            "Posted": posted_date,
            "Eligible Years": years,
            "Job Type": job_type,
            "Skills": skills,
            "Apply URL": apply_url,
            "Company Logo": logo_url
        }

        jobs_data.append(job_entry)

# Define CSV path
csv_file = "regular.csv"

# Load old data if it exists
if os.path.exists(csv_file):
    try:
        existing_df = pd.read_csv(csv_file, encoding="utf-8")
    except UnicodeDecodeError:
        existing_df = pd.read_csv(csv_file, encoding="ISO-8859-1")  # fallback
else:
    existing_df = pd.DataFrame()

# Create DataFrame for new scrape
new_df = pd.DataFrame(jobs_data)

# Merge and deduplicate
combined_df = pd.concat([existing_df, new_df], ignore_index=True)
combined_df.drop_duplicates(inplace=True)

# Save to CSV with UTF-8 encoding
combined_df.to_csv(csv_file, index=False, encoding="utf-8-sig")  # use utf-8-sig for Excel compatibility

print(f"✅ Scraping done. Total jobs in file: {len(combined_df)}")
print(f"➕ New jobs added: {len(combined_df) - len(existing_df)}")
