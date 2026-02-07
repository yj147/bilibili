import asyncio
import os
import random
from bilibili_auth import BilibiliAuth
from reporting_manager import ReportingManager
from auto_reply_service import AutoReplyService
from bilibili_client import BilibiliClient
from utils import resolve_url, parse_bilibili_input

async def report_fallback(auth, target_id, reason):
    """当标准举报接口报错时，通过官方视频通道投递线索。"""
    client = BilibiliClient(auth, 0)
    aid = 2 # 官号视频载体
    url = 'https://api.bilibili.com/x/web-interface/archive/report'
    data = {
        'aid': aid,
        'reason': 1,
        'content': f'【违规线索举报】ID: {target_id} 涉及gac违规站点导流。请核实并封禁。理由: {reason}',
        'csrf': client.cookies.get('bili_jct')
    }
    return await client._post(url, data=data)

async def one_click_justice(auth, target_input, reason):
    print(f"\n--- 启动一键制裁流程 ---")
    url = await resolve_url(target_input)
    info = parse_bilibili_input(url)
    
    if not info:
        print(f"无法解析目标: {target_input}")
        return

    manager = ReportingManager(auth)
    client = BilibiliClient(auth, 0)

    if info["type"] == "video":
        bvid = info["id"]
        print(f"目标视频: {bvid}")
        v_data = await client.get_video_info(bvid)
        if v_data.get("code") == 0:
            aid = v_data["data"]["aid"]
            mid = v_data["data"]["owner"]["mid"]
            
            print("正在批量举报视频...")
            await manager.mass_report_video(aid, 1, reason)
            
            print("正在清洗评论区...")
            await manager.mass_report_comment_section(aid, 1, reason)
            
            print(f"正在举报 UP 主 ({mid})...")
            res = await manager.mass_report_user(mid, reason)
            if any(r.get("result", {}).get("code") == -400 for r in res if "result" in r):
                print("检测到特殊 ID，正在通过线索通道投递...")
                await report_fallback(auth, mid, reason)
        else:
            print("获取视频信息失败。")

    else:
        mid = info["id"]
        print(f"目标用户: {mid}")
        res = await manager.mass_report_user(mid, reason)
        if any(r.get("result", {}).get("code") == -400 for r in res if "result" in r):
            print("检测到特殊 ID，正在通过线索通道投递...")
            await report_fallback(auth, mid, reason)

async def main():
    print("\n" + "="*50)
    print("   Bilibili 自动化打击系统 (CLI 稳定版)")
    print("="*50)
    
    auth = BilibiliAuth()
    if not auth.accounts:
        print("错误: 未检测到账号。请运行 python3 login_helper.py")
        return

    await auth.refresh_wbi_keys()
    
    print("\n模式选择:")
    print("1. 一键制裁套餐 (视频+评论+用户)")
    print("2. 开启多账号私信自动回复")
    print("3. 全能模式 (制裁 + 后台自动回复)")
    
    choice = input("\n请选择 (1/2/3): ").strip()
    
    if choice in ["1", "3"]:
        target = input("请输入目标 (链接/BV/UID): ").strip()
        reason = "违规gac站点导流，传播有害信息，散布虚假广告。"
        
        if choice == "3":
            reply_service = AutoReplyService(auth)
            asyncio.create_task(reply_service.start())
            print("[系统] 自动回复服务已在后台开启。")
            
        await one_click_justice(auth, target, reason)
        print("\n[系统] 所有打击任务已执行完毕。")
        if choice == "3":
            print("按 Ctrl+C 停止后台服务并退出。")
            while True: await asyncio.sleep(3600)
            
    elif choice == "2":
        reply_service = AutoReplyService(auth)
        await reply_service.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n已安全退出。")