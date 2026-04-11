from .pricing import PricingEngine

def main():
    print("--- PetSC 宠物托运智能合约模拟系统 ---")
    
    # 模拟用户输入的需求
    req = {
        "transport_method": "航空托运",
        "distance": 1200,      # 公里
        "weight": 10,          # 公斤
        "is_short_nose": True, # 是否短鼻腔（加倍保险）
        "need_pickup": True,   # 需要上门接宠
        "box_type": "2号箱"     # 航空箱类型
    }
    
    print("\n[业务场景]: 自动报价")
    print(f"托运需求: {req}")
    
    engine = PricingEngine()
    quote = engine.generate_quote(req)
    
    print("\n>>> 生成的报价单明细 <<<")
    for k, v in quote.items():
        print(f" - {k}: ¥{v}")

if __name__ == "__main__":
    main()
