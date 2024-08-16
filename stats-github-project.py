import os
import json
import argparse
import requests
from dotenv import load_dotenv
from datetime import datetime
import glob
import matplotlib.pyplot as plt
import pandas as pd

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
    # response = requests.get(url, headers=headers)
    # contributors = response.json()
    # return contributors
    all_contributors = []
    page = 1
    while True:
        # 准备请求参数
        params = {
            "per_page": 100,  # 每页的数量
            "page": page,  # 当前页码
        }
        # 发送请求
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print("Failed to fetch contributors:", response.json())
            break
        contributors = response.json()
        # 将当前页的贡献者添加到列表
        all_contributors.extend(contributors)
        # 如果返回的贡献者数量小于每页的数量，则没有更多页
        if len(contributors) < params["per_page"]:
            break
        page += 1
    return all_contributors


# 获取issue列表
def get_issues(owner, repo):
    url = f"{BASE_URL}{owner}/{repo}/issues"
    # params = {
    #     "state": "all",  # 获取所有状态的issue
    #     "sort": "created",  # 按创建时间排序
    #     "direction": "desc",  # 降序
    # }
    # response = requests.get(url, headers=headers, params=params)
    # issues = response.json()
    # return issues
    all_issues = []
    page = 1
    while True:
        # 准备请求参数
        params = {
            "state": "all",  # 获取所有状态的issues
            "per_page": 100,  # 每页的数量
            "page": page,  # 当前页码
        }
        # 发送请求
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print("Failed to fetch issues:", response.json())
            break
        issues = response.json()
        # 将当前页的issues添加到列表
        all_issues.extend(issues)
        # 如果返回的issues数量小于每页的数量，则没有更多页
        if len(issues) < params["per_page"]:
            break
        page += 1
    return all_issues


# 获取PR列表
def get_pulls(owner, repo):
    url = f"{BASE_URL}{owner}/{repo}/pulls"
    # response = requests.get(url, headers=headers)
    # pulls = response.json()
    # return pulls
    all_pulls = []
    page = 1
    while True:
        # 准备请求参数
        params = {
            "state": "all",  # 获取所有状态的PRs
            "per_page": 100,  # 每页的数量
            "page": page,  # 当前页码
        }
        # 发送请求
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print("Failed to fetch pulls:", response.json())
            break
        pulls = response.json()
        # 将当前页的PRs添加到列表
        all_pulls.extend(pulls)
        # 如果返回的PRs数量小于每页的数量，则没有更多页
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

    # 从环境变量中读取成员列表
    members_str = os.getenv(
        "MEMBERS_LIST", default="[]"
    )  # 默认为空列表以防环境变量未设置
    members = json.loads(members_str)

    if not args.only_json:
        print(f"内部成员列表({len(members)} 个)：")
        for member in members:
            print(member)
        print()
    result["internal_members_count"] = len(members)
    result["internal_members"] = members

    # issue_users = [
    #     issue["user"]["login"]
    #     for issue in issues
    #     if is_external_contributor(issue["user"]["login"], members)
    # ]
    # issue_users = list(set(issue_users))
    # print("issue 数量：", len(issues))
    # print("issue 用户列表：")
    # for user in issue_users:
    #     print(user)
    # print()

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

    # 打印外部参与者名单
    # print("外部参与者名单：")
    # for contributor in contributors:
    #     if is_external_contributor(contributor, members):
    #         print(contributor["login"])

    # # 将结果写入CSV文件
    # with open("external_contributors.csv", "w", newline="", encoding="utf-8") as file:
    #     writer = csv.writer(file)
    #     writer.writerow(["Login", "Contributions"])
    #     for contributor in contributors:
    #         if is_external_contributor(contributor, members):
    #             writer.writerow([contributor["login"], contributor["contributions"]])

    if not args.only_json:
        print(f"外部用户提交的issue数量：{len(external_issues)}")
        print(f"外部用户提交的PR数量：{len(external_pulls)}")
        print()
        print("外部用户提交的issue列表：")
        for issue in external_issues:
            # print(issue)
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

    # 统计外部参与者的issue和PR
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


def update_chart():
    # 定义数据收集的变量
    data_files = glob.glob("data/*.json")  # 匹配data目录下所有的JSON文件
    all_data = []

    # 遍历所有的JSON文件
    for file_path in data_files:
        with open(file_path, "r") as file:
            data = json.load(file)

            # 将ISO格式的时间字符串转换为datetime对象
            current_time = datetime.fromisoformat(data["current_time"])

            # 提取指标
            external_issues_count = data.get("external_issues_count", 0)
            external_pulls_count = data.get("external_pulls_count", 0)
            external_contributors_count = data.get("external_contributors_count", 0)
            external_participants_count = data.get("external_participants_count", 0)

            # 将提取的数据添加到列表中
            all_data.append(
                {
                    "current_time": current_time,
                    "external_issues_count": external_issues_count,
                    "external_pulls_count": external_pulls_count,
                    "external_contributors_count": external_contributors_count,
                    "external_participants_count": external_participants_count,
                }
            )

    # 将数据转换为DataFrame
    df = pd.DataFrame(all_data)

    # 绘制折线图
    for column in [
        "external_issues_count",
        "external_pulls_count",
        "external_contributors_count",
        "external_participants_count",
    ]:
        plt.figure(figsize=(10, 5))  # 设置图表大小
        plt.plot(df["current_time"], df[column], marker="o")  # 绘制折线图
        plt.xlabel("Date")
        plt.ylabel(column)
        plt.title(f"{column} Over Time")

        # 保存图表
        plt.savefig(f"chart/{column}_over_time.png")
        plt.close()

    # 可以添加更多的图表绘制逻辑
    # ...

    print("Charts have been saved to the 'chart' directory.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="This is a stats script for gitHub project"
    )

    # 添加参数
    parser.add_argument("--only_json", action="store_true", help="Only output JSON")

    # 解析参数
    args = parser.parse_args()

    # 记录当前时间
    current_time = datetime.now().isoformat()
    result = main(args)
    # 将开始时间添加到 result 字典中
    result["current_time"] = current_time
    if args.only_json:
        print(json.dumps(result, indent=4))

    # 更新图表
    update_chart()
