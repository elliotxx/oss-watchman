import os
import json
import argparse
import requests
import pytz
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()  # 默认从当前目录下的 .env 文件加载

# 替换为你的GitHub访问令牌
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
# 替换为你的目标仓库，格式为：'owner/repo'
REPO = os.environ.get("REPO")

# GitHub API的基础URL
BASE_URL = "https://api.github.com/repos/"

# 发送请求的headers，包含认证信息
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


# 获取贡献者列表
def get_contributors(owner, repo):
    url = f"{BASE_URL}{owner}/{repo}/contributors"
    all_contributors = []
    page = 1
    while True:
        params = {
            "per_page": 100,  # 每页的数量
            "page": page,  # 当前页码
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print("Failed to fetch contributors:", response.json())
            break
        contributors = response.json()
        all_contributors.extend(contributors)
        if len(contributors) < params["per_page"]:
            break
        page += 1
    return all_contributors


# 获取issue列表
def get_issues(owner, repo):
    url = f"{BASE_URL}{owner}/{repo}/issues"
    all_issues = []
    page = 1
    while True:
        params = {
            "state": "all",  # 获取所有状态的issues
            "per_page": 100,  # 每页的数量
            "page": page,  # 当前页码
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print("Failed to fetch issues:", response.json())
            break
        issues = response.json()
        all_issues.extend(issues)
        if len(issues) < params["per_page"]:
            break
        page += 1
    return all_issues


# 获取PR列表
def get_pulls(owner, repo):
    url = f"{BASE_URL}{owner}/{repo}/pulls"
    all_pulls = []
    page = 1
    while True:
        params = {
            "state": "all",  # 获取所有状态的PRs
            "per_page": 100,  # 每页的数量
            "page": page,  # 当前页码
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print("Failed to fetch pulls:", response.json())
            break
        pulls = response.json()
        all_pulls.extend(pulls)
        if len(pulls) < params["per_page"]:
            break
        page += 1
    return all_pulls


# 检查用户是否是外部参与者
def is_external_contributor(contributor, members):
    return contributor not in members


# 主函数
def main(args):
    result = {}

    owner, repo = REPO.split("/")
    if not args.only_json:
        print("开始获取所有贡献者...")
    contributors = get_contributors(owner, repo)

    if not args.only_json:
        print("开始获取所有Issue...")
    issues = get_issues(owner, repo)

    if not args.only_json:
        print("开始获取所有PR...")
    pulls = get_pulls(owner, repo)
    if not args.only_json:
        print()

    members_str = os.getenv("MEMBERS_LIST", default="[]")
    members = json.loads(members_str)

    if not args.only_json:
        print(f"内部成员列表({len(members)} 个)：")
        for member in members:
            print(member)
        print()
    result["internal_members_count"] = len(members)
    result["internal_members"] = members

    # 过滤指定时间之前的Issue和PR
    if args.before:
        before_time = datetime.fromisoformat(args.before).replace(tzinfo=pytz.UTC)
        issues = [issue for issue in issues if datetime.fromisoformat(issue["created_at"]) <= before_time]
        pulls = [pull for pull in pulls if datetime.fromisoformat(pull["created_at"]) <= before_time]

    external_issues = [
        issue
        for issue in issues
        if is_external_contributor(issue["user"]["login"], members)
        and "pull_request" not in issue
    ]
    external_pulls = [
        pull
        for pull in pulls
        if is_external_contributor(pull["user"]["login"], members)
    ]

    if not args.only_json:
        print(f"外部用户提交的issue数量：{len(external_issues)}")
        print(f"外部用户提交的PR数量：{len(external_pulls)}")
        print()
        print("外部用户提交的issue列表：")
        for issue in external_issues:
            print(issue["title"] + " by " + issue["user"]["login"])
        print()

        print("外部用户提交的PR列表：")
        for pull in external_pulls:
            print(pull["title"] + " by " + pull["user"]["login"])
        print()

    result["external_issues_count"] = len(external_issues)
    result["external_issues"] = [
        {"title": issue["title"], "user": issue["user"]["login"]}
        for issue in external_issues
    ]
    result["external_pulls_count"] = len(external_pulls)
    result["external_pulls"] = [
        {"title": pull["title"], "user": pull["user"]["login"]}
        for pull in external_pulls
    ]

    external_contributors = [
        contributor["login"]
        for contributor in contributors
        if contributor["login"] not in members
    ]
    for pull in external_pulls:
        if is_external_contributor(pull["user"]["login"], members):
            external_contributors.append(pull["user"]["login"])
    external_contributors = list(set(external_contributors))

    if not args.only_json:
        print(
            f"外部贡献者(向项目提交了 PR 的外部用户)列表({len(external_contributors)} 个)："
        )
        for contributor in external_contributors:
            print(contributor)
        print()
    result["external_contributors_count"] = len(external_contributors)
    result["external_contributors"] = external_contributors

    external_participants = [
        issue["user"]["login"]
        for issue in issues
        if is_external_contributor(issue["user"]["login"], members)
    ]
    external_participants += [
        pull["user"]["login"]
        for pull in pulls
        if is_external_contributor(pull["user"]["login"], members)
    ]
    external_participants = list(set(external_participants))

    if not args.only_json:
        print(
            f"外部社区参与者(参与了社区的外部用户, 参与社区包括代码修改、参与讨论、提需求等)列表({len(external_participants)} 个)："
        )
        for user in external_participants:
            print(user)
        print()

    result["external_participants_count"] = len(external_participants)
    result["external_participants"] = external_participants

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="This is a stats script for gitHub project"
    )

    # 添加参数
    parser.add_argument("--only_json", action="store_true", help="Only output JSON")
    parser.add_argument("--before", type=str, help="Filter issues and PRs before this date (ISO 8601 format)")
    parser.add_argument("--fix-data", action="store_true", help="Fix data in the 'data' directory")

    # 解析参数
    args = parser.parse_args()

    # 从环境变量中读取时区
    timezone_str = os.getenv("TZ", "UTC")  # 默认时区设置为'UTC'
    timezone = pytz.timezone(timezone_str)

    # 记录当前时间
    current_time = datetime.now(timezone).isoformat()

    if args.fix_data:
        data_dir = "data"
        for filename in os.listdir(data_dir):
            if filename.startswith("stats-") and filename.endswith(".json"):
                file_path = os.path.join(data_dir, filename)
                # 从 json 文件中提取 current_time 作为 before_time
                with open(file_path, "r") as f:
                    data = json.load(f)
                    before_time = data.get("current_time", None)
                if not before_time:
                    print(f"未提取到 before_time，跳过文件 {file_path}")
                    continue
                args.before = before_time
                args.only_json = True
                result = main(args)
                result["current_time"] = before_time
                # 覆盖原文件
                with open(file_path, "w") as f:
                    json.dump(result, f, indent=4)
                print(f"Updated {file_path}")
    else:
        result = main(args)
        # 将开始时间添加到 result 字典中
        result["current_time"] = current_time
        if args.only_json:
            print(json.dumps(result, indent=4))