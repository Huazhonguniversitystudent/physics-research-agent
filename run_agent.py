from src.agent import run_agent


def main() -> None:
    print("Physics Research Agent - Day 4")
    print("支持：物理问答、数学/物理工具、synthetic CSV、注册的真实科研 CSV、switching time、曲线比较和绘图。")

    while True:
        question = input("输入问题（输入 exit 退出）：").strip()
        if question.lower() == "exit":
            break
        if not question:
            continue

        try:
            answer = run_agent(question)
        except Exception as exc:
            print(f"运行失败：{exc}")
        else:
            print(f"\nAI 回答：\n{answer}\n")


if __name__ == "__main__":
    main()
