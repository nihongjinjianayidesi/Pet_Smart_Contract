class PricingEngine:
    """自动报价引擎：负责宠物托运各项费用的核算"""
    
    def __init__(self):
        # 基础保险费率为 2000元保额收200元（示例比例，这里按你附录的：基础2000元内，每增加10元加收100元，此处做简化模拟）
        self.base_insurance_fee = 200.0 
        
    def calculate_base_fee(self, transport_method, distance, weight):
        """计算基础运费"""
        base_fee = 0.0
        if transport_method == "航空托运":
            base_fee = weight * 30.0 + 100.0  # 模拟计费
        elif transport_method == "顺风车托运" or transport_method == "陆运专车":
            base_fee = distance * 2.5 + 50.0  # 模拟计费
        elif transport_method == "铁路托运":
            base_fee = distance * 1.5 + 80.0  # 模拟计费
        return base_fee

    def calculate_additional_fee(self, is_short_nose, need_pickup, box_type, distance):
        """计算附加费用（接宠、笼具、保险等）"""
        additional_fee = 0.0
        
        # 短鼻腔宠物建议购买双倍保险
        if is_short_nose:
            additional_fee += self.base_insurance_fee * 2
        else:
            additional_fee += self.base_insurance_fee
            
        # 上门接宠费 (0-50公里免费，50-100公里50元，以上暂定100元)
        if need_pickup:
            if 50 < distance <= 100:
                additional_fee += 50.0
            elif distance > 100:
                additional_fee += 100.0
                
        # 笼具费
        if box_type == "1号箱":
            additional_fee += 30.0
        elif box_type == "2号箱":
            additional_fee += 50.0
        elif box_type == "3号箱":
            additional_fee += 80.0
            
        return additional_fee

    def generate_quote(self, req):
        """
        生成完整报价单
        req 包含: transport_method, distance, weight, is_short_nose, need_pickup, box_type
        """
        base = self.calculate_base_fee(req['transport_method'], req['distance'], req['weight'])
        additional = self.calculate_additional_fee(
            req['is_short_nose'], req['need_pickup'], req['box_type'], req['distance']
        )
        
        total_fee = base + additional
        deposit = total_fee * 0.10  # 10%违约金预留
        
        return {
            "基础运费": round(base, 2),
            "附加费用": round(additional, 2),
            "总费用": round(total_fee, 2),
            "违约金预留(10%)": round(deposit, 2),
            "需支付金额": round(total_fee + deposit, 2)
        }
