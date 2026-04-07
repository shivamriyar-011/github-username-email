import requests
import os
import sys
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("GH_SAML_TOKEN")
HEADERS = {'Authorization': f'token {TOKEN}'}


def get_email_from_events(username):
    """Try to find email from the user's recent public events (push events)."""
    url = f"https://api.github.com/users/{username}/events/public"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        return []

    emails = set()
    for event in response.json():
        if event.get("type") == "PushEvent":
            for commit in event.get("payload", {}).get("commits", []):
                author = commit.get("author", {})
                email = author.get("email", "")
                if email and "noreply" not in email:
                    emails.add(email)
    return list(emails)


def get_email_from_patches(username):
    """Try to find email from recent commit patches."""
    repos_url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=5"
    response = requests.get(repos_url, headers=HEADERS)
    if response.status_code != 200:
        return []

    emails = set()
    for repo in response.json():
        if repo.get("fork"):
            continue
        repo_name = repo["full_name"]
        commits_url = f"https://api.github.com/repos/{repo_name}/commits?per_page=5"
        commits_resp = requests.get(commits_url, headers=HEADERS)
        if commits_resp.status_code != 200:
            continue

        for commit in commits_resp.json():
            # Check if this commit is by the target user
            author_login = (commit.get("author") or {}).get("login", "")
            if author_login.lower() != username.lower():
                continue

            commit_data = commit.get("commit", {})
            author_info = commit_data.get("author", {})
            email = author_info.get("email", "")
            if email and "noreply" not in email:
                emails.add(email)
    return list(emails)


def get_email_from_profile(username):
    """Check if the user has a public email on their profile."""
    url = f"https://api.github.com/users/{username}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Error: User '{username}' not found (HTTP {response.status_code})")
        return None

    data = response.json()
    profile_info = {
        "name": data.get("name"),
        "blog": data.get("blog"),
        "company": data.get("company"),
        "location": data.get("location"),
        "bio": data.get("bio"),
    }

    email = data.get("email")
    return email, profile_info


def main():
    if len(sys.argv) < 2:
        username = input("Enter GitHub username: ").strip()
    else:
        username = sys.argv[1]

    if not username:
        print("Error: Username is required.")
        sys.exit(1)

    print(f"\n🔍 Looking up email for GitHub user: {username}\n")

    # 1. Check profile
    result = get_email_from_profile(username)
    if result is None:
        sys.exit(1)

    profile_email, profile_info = result

    # Print profile info
    name = profile_info.get("name")
    if name:
        print(f"  Name:     {name}")
    company = profile_info.get("company")
    if company:
        print(f"  Company:  {company}")
    location = profile_info.get("location")
    if location:
        print(f"  Location: {location}")
    print()

    all_emails = set()

    if profile_email:
        all_emails.add(profile_email)
        print(f"✅ Public profile email: {profile_email}")

    # 2. Check public events
    event_emails = get_email_from_events(username)
    for e in event_emails:
        all_emails.add(e)

    # 3. Check commit patches
    patch_emails = get_email_from_patches(username)
    for e in patch_emails:
        all_emails.add(e)

    if all_emails:
        print(f"\n Found {len(all_emails)} email(s) for {username}:")
        for email in sorted(all_emails):
            print(f"   • {email}")
    else:
        print(f"\n No public email found for {username}.")
        print("   The user may have their email set to private.")


if __name__ == "__main__":
    main()