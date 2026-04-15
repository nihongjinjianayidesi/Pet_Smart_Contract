-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);

-- 创建宠物表
CREATE TABLE IF NOT EXISTS pets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    breed VARCHAR(100),
    age INTEGER,
    photo_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_pets_user_id ON pets(user_id);

-- 创建运输订单表
CREATE TABLE IF NOT EXISTS transport_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id UUID REFERENCES pets(id) ON DELETE CASCADE,
    tracking_number VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT '待收件',
    current_location JSONB,
    estimated_arrival TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_orders_pet_id ON transport_orders(pet_id);
CREATE INDEX IF NOT EXISTS idx_orders_tracking_number ON transport_orders(tracking_number);

-- 创建跟踪更新表
CREATE TABLE IF NOT EXISTS tracking_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES transport_orders(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    location VARCHAR(200),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_updates_order_id ON tracking_updates(order_id);
CREATE INDEX IF NOT EXISTS idx_updates_created_at ON tracking_updates(created_at DESC);

-- 启用RLS
ALTER TABLE pets ENABLE ROW LEVEL SECURITY;
ALTER TABLE transport_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE tracking_updates ENABLE ROW LEVEL SECURITY;

-- 宠物表RLS策略
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'pets' AND policyname = '用户只能查看自己的宠物'
    ) THEN
        CREATE POLICY "用户只能查看自己的宠物" ON pets
            FOR SELECT USING (auth.uid()::uuid = user_id);
    END IF;
END $$;

-- 运输订单表RLS策略
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'transport_orders' AND policyname = '用户只能查看自己宠物的订单'
    ) THEN
        CREATE POLICY "用户只能查看自己宠物的订单" ON transport_orders
            FOR SELECT USING (
                pet_id IN (SELECT id FROM pets WHERE user_id = auth.uid()::uuid)
            );
    END IF;
END $$;

-- 授权访问
GRANT SELECT ON pets TO authenticated;
GRANT SELECT ON transport_orders TO authenticated;
GRANT SELECT ON tracking_updates TO authenticated;
