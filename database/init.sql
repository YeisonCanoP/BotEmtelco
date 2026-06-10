BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

-- =========================================================
-- FUNCIONES
-- =========================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =========================================================
-- TABLAS
-- =========================================================

CREATE TABLE IF NOT EXISTS products (
    sku         VARCHAR(30)     PRIMARY KEY,
    name        VARCHAR(150)    NOT NULL,
    category    VARCHAR(50)     NOT NULL,
    description TEXT            NOT NULL DEFAULT '',
    price       NUMERIC(12, 2)  NOT NULL CHECK (price >= 0),
    stock       INTEGER         NOT NULL DEFAULT 0 CHECK (stock >= 0),
    specs       JSONB           NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customers (
    identification  VARCHAR(11)     PRIMARY KEY,
    full_name       VARCHAR(100)    NOT NULL,
    phone           VARCHAR(10)     NOT NULL,
    email           VARCHAR(150)    NOT NULL UNIQUE,
    kind            VARCHAR(20)     NOT NULL DEFAULT 'FREQUENT',
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT customers_identification_format
        CHECK (identification ~ '^[0-9]{4,11}$'),

    CONSTRAINT customers_phone_format
        CHECK (phone ~ '^[36][0-9]{9}$'),

    CONSTRAINT customers_kind_valid
        CHECK (kind IN ('NEW', 'FREQUENT')),

    CONSTRAINT customers_email_format
        CHECK (email LIKE '%@%')
);

CREATE TABLE IF NOT EXISTS orders (
    id                  VARCHAR(30)     PRIMARY KEY,
    customer_id         VARCHAR(11)     NOT NULL,
    status              VARCHAR(30)     NOT NULL,
    estimated_delivery  DATE,
    address             VARCHAR(250)    NOT NULL,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers (identification),

    CONSTRAINT orders_status_valid
        CHECK (
            status IN (
                'CONFIRMED',
                'PREPARING',
                'SHIPPED',
                'IN_TRANSIT',
                'DELIVERED',
                'CANCELLED'
            )
        )
);

CREATE TABLE IF NOT EXISTS order_items (
    id          BIGSERIAL       PRIMARY KEY,
    order_id    VARCHAR(30)     NOT NULL,
    product_sku VARCHAR(30)     NOT NULL,
    quantity    INTEGER         NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price  NUMERIC(12, 2)  NOT NULL CHECK (unit_price >= 0),
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id)
        REFERENCES orders (id),

    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_sku)
        REFERENCES products (sku),

    CONSTRAINT order_items_order_product_unique
        UNIQUE (order_id, product_sku)
);

CREATE TABLE IF NOT EXISTS warranties (
    id          VARCHAR(30)     PRIMARY KEY,
    product_sku VARCHAR(30)     NOT NULL,
    order_id    VARCHAR(30)     NOT NULL,
    active      BOOLEAN         NOT NULL DEFAULT TRUE,
    starts_on   DATE            NOT NULL,
    expires_on  DATE            NOT NULL,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_warranties_product
        FOREIGN KEY (product_sku)
        REFERENCES products (sku),

    CONSTRAINT fk_warranties_order
        FOREIGN KEY (order_id)
        REFERENCES orders (id),

    CONSTRAINT warranties_dates_valid
        CHECK (expires_on >= starts_on),

    CONSTRAINT warranties_order_product_unique
        UNIQUE (order_id, product_sku)
);

CREATE TABLE IF NOT EXISTS warranty_claims (
    id              VARCHAR(40)     PRIMARY KEY,
    warranty_id     VARCHAR(30)     NOT NULL,
    customer_id     VARCHAR(11)     NOT NULL,
    description     TEXT            NOT NULL,
    status          VARCHAR(30)     NOT NULL DEFAULT 'OPEN',
    requires_human  BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_claims_warranty
        FOREIGN KEY (warranty_id)
        REFERENCES warranties (id),

    CONSTRAINT fk_claims_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers (identification),

    CONSTRAINT warranty_claim_status_valid
        CHECK (
            status IN (
                'OPEN',
                'IN_REVIEW',
                'ESCALATED',
                'RESOLVED',
                'REJECTED'
            )
        )
);

CREATE TABLE IF NOT EXISTS kb_chunks (
    id          BIGSERIAL       PRIMARY KEY,
    source      VARCHAR(255)    NOT NULL,
    title       VARCHAR(255)    NOT NULL,
    content     TEXT            NOT NULL,
    metadata    JSONB           NOT NULL DEFAULT '{}'::jsonb,
    embedding   VECTOR(1536)    DEFAULT NULL, -- se llena en el paso de ingesta
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- TRIGGERS updated_at
-- =========================================================

CREATE OR REPLACE TRIGGER trg_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE TRIGGER trg_warranty_claims_updated_at
    BEFORE UPDATE ON warranty_claims
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =========================================================
-- ÍNDICES
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_products_category
    ON products (category);

CREATE INDEX IF NOT EXISTS idx_products_price
    ON products (price);

CREATE INDEX IF NOT EXISTS idx_products_specs
    ON products USING GIN (specs);

CREATE INDEX IF NOT EXISTS idx_order_items_order
    ON order_items (order_id);

CREATE INDEX IF NOT EXISTS idx_order_items_product
    ON order_items (product_sku);

CREATE INDEX IF NOT EXISTS idx_orders_customer
    ON orders (customer_id);

CREATE INDEX IF NOT EXISTS idx_orders_status
    ON orders (status);

CREATE INDEX IF NOT EXISTS idx_warranties_order
    ON warranties (order_id);

CREATE INDEX IF NOT EXISTS idx_warranties_product
    ON warranties (product_sku);

CREATE INDEX IF NOT EXISTS idx_claims_customer
    ON warranty_claims (customer_id);

-- El índice vectorial se crea después de insertar los embeddings:
-- CREATE INDEX idx_kb_chunks_embedding
--     ON kb_chunks USING hnsw (embedding vector_cosine_ops);

-- =========================================================
-- PRODUCTOS: 12 REGISTROS
-- =========================================================

INSERT INTO products (sku, name, category, description, price, stock, specs)
VALUES
(
    'LAP-DES-001',
    'ASUS Vivobook Pro 15 OLED',
    'LAPTOP',
    'Portátil recomendado para diseño gráfico y creación de contenido.',
    4799900,
    8,
    '{
        "processor": "AMD Ryzen 7",
        "ram_gb": 16,
        "storage": "1 TB SSD",
        "gpu": "NVIDIA RTX 3050 6 GB",
        "display": "15.6 OLED",
        "resolution": "2.8K",
        "recommended_for": ["diseño gráfico", "fotografía", "edición de video"]
    }'::jsonb
),
(
    'LAP-DES-002',
    'Lenovo LOQ 15',
    'LAPTOP',
    'Portátil de alto rendimiento con tarjeta gráfica dedicada.',
    4499900,
    5,
    '{
        "processor": "Intel Core i5",
        "ram_gb": 16,
        "storage": "512 GB SSD",
        "gpu": "NVIDIA RTX 4050 6 GB",
        "display": "15.6 IPS",
        "resolution": "Full HD",
        "recommended_for": ["diseño gráfico", "modelado 3D", "gaming"]
    }'::jsonb
),
(
    'LAP-DES-003',
    'Acer Swift Go 14 OLED',
    'LAPTOP',
    'Portátil liviano con pantalla OLED para trabajo creativo.',
    3999900,
    6,
    '{
        "processor": "Intel Core Ultra 5",
        "ram_gb": 16,
        "storage": "512 GB SSD",
        "gpu": "Intel Arc integrada",
        "display": "14 OLED",
        "resolution": "2.8K",
        "recommended_for": ["diseño gráfico", "ilustración", "movilidad"]
    }'::jsonb
),
(
    'LAP-OFF-001',
    'HP Pavilion 15',
    'LAPTOP',
    'Portátil para productividad, estudio y tareas de oficina.',
    2899900,
    10,
    '{
        "processor": "Intel Core i5",
        "ram_gb": 8,
        "storage": "512 GB SSD",
        "gpu": "Intel Iris Xe",
        "display": "15.6 IPS",
        "resolution": "Full HD",
        "recommended_for": ["oficina", "estudio", "navegación"]
    }'::jsonb
),
(
    'LAP-PRO-001',
    'MacBook Pro 14',
    'LAPTOP',
    'Equipo profesional para diseño y edición audiovisual.',
    8999900,
    3,
    '{
        "processor": "Apple M3 Pro",
        "ram_gb": 18,
        "storage": "512 GB SSD",
        "gpu": "GPU integrada Apple",
        "display": "14.2 Liquid Retina XDR",
        "resolution": "3024x1964",
        "recommended_for": ["diseño profesional", "edición de video", "producción"]
    }'::jsonb
),
(
    'TV-LG-001',
    'LG OLED evo 55 pulgadas',
    'TELEVISION',
    'Televisor OLED 4K con funciones inteligentes.',
    4299900,
    4,
    '{
        "size_inches": 55,
        "resolution": "4K",
        "panel": "OLED",
        "operating_system": "webOS",
        "hdmi_ports": 4
    }'::jsonb
),
(
    'TV-SAM-001',
    'Samsung Crystal UHD 55 pulgadas',
    'TELEVISION',
    'Televisor inteligente 4K para entretenimiento en el hogar.',
    2399900,
    7,
    '{
        "size_inches": 55,
        "resolution": "4K",
        "panel": "LED",
        "operating_system": "Tizen",
        "hdmi_ports": 3
    }'::jsonb
),
(
    'TV-TCL-001',
    'TCL QLED 50 pulgadas',
    'TELEVISION',
    'Televisor QLED con Google TV.',
    1999900,
    0,
    '{
        "size_inches": 50,
        "resolution": "4K",
        "panel": "QLED",
        "operating_system": "Google TV",
        "hdmi_ports": 3
    }'::jsonb
),
(
    'CEL-SAM-001',
    'Samsung Galaxy S24',
    'CELULAR',
    'Celular de gama alta con cámara avanzada.',
    3899900,
    12,
    '{
        "storage": "256 GB",
        "ram_gb": 8,
        "display": "6.2 AMOLED",
        "camera": "50 MP",
        "network": "5G"
    }'::jsonb
),
(
    'CEL-XIA-001',
    'Xiaomi Redmi Note 13 Pro',
    'CELULAR',
    'Celular de gama media con cámara de alta resolución.',
    1599900,
    15,
    '{
        "storage": "256 GB",
        "ram_gb": 8,
        "display": "6.67 AMOLED",
        "camera": "200 MP",
        "network": "5G"
    }'::jsonb
),
(
    'ACC-MON-001',
    'Monitor LG UltraGear 27',
    'ACCESSORY',
    'Monitor IPS de alta frecuencia para trabajo y entretenimiento.',
    1399900,
    9,
    '{
        "size_inches": 27,
        "resolution": "QHD",
        "panel": "IPS",
        "refresh_rate_hz": 165
    }'::jsonb
),
(
    'ACC-MOU-001',
    'Mouse Logitech MX Master 3S',
    'ACCESSORY',
    'Mouse inalámbrico ergonómico para productividad.',
    449900,
    20,
    '{
        "connection": ["Bluetooth", "USB"],
        "wireless": true,
        "recommended_for": ["diseño", "productividad"]
    }'::jsonb
)
ON CONFLICT (sku) DO NOTHING;

-- =========================================================
-- CLIENTES
-- =========================================================

INSERT INTO customers (identification, full_name, phone, email, kind)
VALUES
(
    '1020304050',
    'María Gómez',
    '3001234567',
    'maria.gomez@example.com',
    'FREQUENT'
),
(
    '987654321',
    'Carlos Rodríguez',
    '3109876543',
    'carlos.rodriguez@example.com',
    'FREQUENT'
),
(
    '456789123',
    'Laura Martínez',
    '6012345678',
    'laura.martinez@example.com',
    'FREQUENT'
),
(
    '1234567890',
    'Andrés Pérez',
    '3204567890',
    'andres.perez@example.com',
    'FREQUENT'
)
ON CONFLICT (identification) DO NOTHING;

-- =========================================================
-- PEDIDOS CON ESTADOS VARIADOS
-- =========================================================

INSERT INTO orders (id, customer_id, status, estimated_delivery, address)
VALUES
(
    'ORD-1001',
    '1020304050',
    'IN_TRANSIT',
    CURRENT_DATE + 2,
    'Carrera 43A # 10-25, Medellín'
),
(
    'ORD-1002',
    '987654321',
    'DELIVERED',
    CURRENT_DATE - 30,
    'Calle 100 # 15-40, Bogotá'
),
(
    'ORD-1003',
    '456789123',
    'PREPARING',
    CURRENT_DATE + 5,
    'Avenida 6N # 24-30, Cali'
),
(
    'ORD-1004',
    '1234567890',
    'SHIPPED',
    CURRENT_DATE + 3,
    'Carrera 53 # 80-67, Barranquilla'
),
(
    'ORD-1005',
    '1020304050',
    'CANCELLED',
    NULL,
    'Carrera 43A # 10-25, Medellín'
)
ON CONFLICT (id) DO NOTHING;

-- =========================================================
-- LÍNEAS DE PEDIDO
-- =========================================================

INSERT INTO order_items (order_id, product_sku, quantity, unit_price)
VALUES
('ORD-1001', 'LAP-DES-001', 1, 4799900),
('ORD-1002', 'TV-LG-001',   1, 4299900),
('ORD-1003', 'CEL-SAM-001', 1, 3899900),
('ORD-1004', 'CEL-XIA-001', 1, 1599900),
('ORD-1005', 'ACC-MON-001', 1, 1399900)
ON CONFLICT (order_id, product_sku) DO NOTHING;

-- =========================================================
-- GARANTÍAS
-- =========================================================

INSERT INTO warranties (id, product_sku, order_id, active, starts_on, expires_on)
VALUES
(
    'WAR-1001',
    'TV-LG-001',
    'ORD-1002',
    TRUE,
    CURRENT_DATE - 180,
    CURRENT_DATE + 185
),
(
    'WAR-1002',
    'LAP-DES-001',
    'ORD-1001',
    TRUE,
    CURRENT_DATE - 90,
    CURRENT_DATE + 275
),
(
    'WAR-1003',
    'CEL-XIA-001',
    'ORD-1004',
    FALSE,
    CURRENT_DATE - 730,
    CURRENT_DATE - 365
)
ON CONFLICT (id) DO NOTHING;

-- =========================================================
-- BASE DE CONOCIMIENTO (sin embeddings aún)
-- =========================================================

INSERT INTO kb_chunks (source, title, content, metadata)
SELECT
    'politica_garantia.md',
    'Condiciones generales de garantía',
    'La garantía cubre defectos de fabricación durante el periodo indicado. No cubre golpes, humedad, manipulación no autorizada o daños causados por fluctuaciones eléctricas.',
    '{"category": "warranty", "language": "es"}'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM kb_chunks
    WHERE source = 'politica_garantia.md'
    AND title  = 'Condiciones generales de garantía'
);

INSERT INTO kb_chunks (source, title, content, metadata)
SELECT
    'politica_devoluciones.md',
    'Política de devoluciones',
    'Las solicitudes de devolución deben registrarse dentro de los cinco días hábiles posteriores a la entrega y el producto debe conservar sus accesorios y empaque.',
    '{"category": "returns", "language": "es"}'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM kb_chunks
    WHERE source = 'politica_devoluciones.md'
    AND title  = 'Política de devoluciones'
);

COMMIT;