import json
import glob
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime


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

    # Sort the data by time before converting to DataFrame
    all_data.sort(key=lambda x: x["current_time"])
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


# 更新图表
if __name__ == "__main__":
    update_chart()
