import os
import json
import argparse
import sys
import requests
import pytz
from dotenv import load_dotenv
from datetime import datetime, timedelta

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
        print("开始获取所有Issue...")
    issues = get_issues(owner, repo)

    if not args.only_json:
        print("开始获取所有PR...")
    pulls = get_pulls(owner, repo)
    if not args.only_json:
        print()

    # 获取预置的内部成员列表
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

    # 统计外部贡献者
    external_contributors = []
    for pull in external_pulls:
        if is_external_contributor(pull["user"]["login"], members):
            external_contributors.append(pull["user"]["login"])
    external_contributors = sorted(list(set(external_contributors)))

    if not args.only_json:
        print(
            f"外部贡献者(向项目提交了 PR 的外部用户)列表({len(external_contributors)} 个)："
        )
        for contributor in external_contributors:
            print(contributor)
        print()
    result["external_contributors_count"] = len(external_contributors)
    result["external_contributors"] = external_contributors

    # 统计外部参与者
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
    external_participants = sorted(list(set(external_participants)))

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

# 获取第一个提交的时间
def get_first_commit_time(owner, repo):
    page = 1
    while True:
        url = f"{BASE_URL}{owner}/{repo}/commits"
        params = {
            "per_page": 100,  # 每页获取100个提交
            "page": page,  # 当前页码
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print("Failed to fetch commits:", response.json())
            return None
        commits = response.json()
        if not commits:
            break
        first_commit_time = commits[-1]["commit"]["author"]["date"]
        page += 1
    return first_commit_time

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="This is a stats script for gitHub project"
    )

    # 添加参数
    parser.add_argument("--only_json", action="store_true", help="Only output JSON")
    parser.add_argument("--before", type=str, help="Filter issues and PRs before this date (ISO 8601 format), e.g., '2024-08-20T15:56:40+08:00', '2024-08-20T07:56:40Z'")
    parser.add_argument("--fix-data", action="store_true", help="Fix data in the 'data' directory")
    parser.add_argument("--complete-data-since", type=str, help="Complete missing data in the 'data' directory starting from this date (ISO 8601 format) or 'FIRST_COMMIT', e.g., '2024-08-20T15:56:40+08:00', '2024-08-20T07:56:40Z'")

    # 解析参数
    args = parser.parse_args()

    # 从环境变量中读取时区
    timezone_str = os.getenv("TZ", "UTC")  # 默认时区设置为'UTC'
    timezone = pytz.timezone(timezone_str)

    # 记录当前时间
    current_time = datetime.now(timezone).isoformat()

    if args.complete_data_since:
        data_dir = "data"
        since_time = None
        if args.complete_data_since == "FIRST_COMMIT":
            # 获取第一个提交的时间
            first_commit_time_str = get_first_commit_time(REPO.split("/")[0], REPO.split("/")[1])
            if first_commit_time_str:
                first_commit_time = datetime.fromisoformat(first_commit_time_str)
            else:
                first_commit_time = None
            if since_time:
                print(f"获取到的第一个提交时间为: {first_commit_time}")
            else:
                print("未能获取到第一个提交时间,退出")
                sys.exit(1)
            since_time = first_commit_time
        else:
            complete_data_since = datetime.fromisoformat(args.complete_data_since)
            since_time = complete_data_since
        print(f"开始处理数据，起始时间为: {since_time}")
        current_time_obj = datetime.now(timezone)
        print(f"当前时间为: {current_time_obj}")
        while since_time <= current_time_obj:
            file_name = f"stats-{since_time.strftime('%Y-%m-%dT%H:%M:%S%z')}.json"
            file_path = os.path.join(data_dir, file_name)
            date_exists = any(file_name.startswith(f"stats-{since_time.strftime('%Y-%m-%d')}") for file_name in os.listdir(data_dir))
            if not date_exists:
                print(f"开始处理日期: {since_time.strftime('%Y-%m-%d')}")
                args.before = since_time.isoformat()
                args.only_json = True
                result = main(args)
                result["current_time"] = since_time.isoformat()
                with open(file_path, "w") as f:
                    json.dump(result, f, indent=4)
                print(f"已创建文件: {file_path}")
            else:
                print(f"日期 {since_time.strftime('%Y-%m-%d')} 已存在，跳过处理")
            since_time += timedelta(days=1)
    elif args.fix_data:
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