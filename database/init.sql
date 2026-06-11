BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

-- =========================================================
-- FUNCIONES
-- =========================================================

CREATE OR REPLACE FUNCTION set_updated_at()
    RETURNS TRIGGER AS
$$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =========================================================
-- TABLAS
-- =========================================================

CREATE TABLE IF NOT EXISTS products
(
    sku         VARCHAR(30) PRIMARY KEY,
    name        VARCHAR(150)   NOT NULL,
    category    VARCHAR(50)    NOT NULL,
    description TEXT           NOT NULL DEFAULT '',
    price       NUMERIC(12, 2) NOT NULL CHECK (price >= 0),
    stock       INTEGER        NOT NULL DEFAULT 0 CHECK (stock >= 0),
    specs       JSONB          NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customers
(
    identification VARCHAR(11) PRIMARY KEY,
    full_name      VARCHAR(100) NOT NULL,
    phone          VARCHAR(10)  NOT NULL,
    email          VARCHAR(150) NOT NULL UNIQUE,
    kind           VARCHAR(20)  NOT NULL DEFAULT 'FREQUENT',
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT customers_identification_format
        CHECK (identification ~ '^[0-9]{4,11}$'),

    CONSTRAINT customers_phone_format
        CHECK (phone ~ '^[36][0-9]{9}$'),

    CONSTRAINT customers_kind_valid
        CHECK (kind IN ('NEW', 'FREQUENT')),

    CONSTRAINT customers_email_format
        CHECK (email LIKE '%@%')
);

CREATE TABLE IF NOT EXISTS orders
(
    id                 VARCHAR(30) PRIMARY KEY,
    customer_id        VARCHAR(11)  NOT NULL,
    status             VARCHAR(30)  NOT NULL,
    estimated_delivery DATE,
    address            VARCHAR(250) NOT NULL,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,

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

CREATE TABLE IF NOT EXISTS order_items
(
    id          BIGSERIAL PRIMARY KEY,
    order_id    VARCHAR(30)    NOT NULL,
    product_sku VARCHAR(30)    NOT NULL,
    quantity    INTEGER        NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price  NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0),
    created_at  TIMESTAMPTZ    NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id)
            REFERENCES orders (id),

    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_sku)
            REFERENCES products (sku),

    CONSTRAINT order_items_order_product_unique
        UNIQUE (order_id, product_sku)
);

CREATE TABLE IF NOT EXISTS warranties
(
    id          VARCHAR(30) PRIMARY KEY,
    product_sku VARCHAR(30) NOT NULL,
    order_id    VARCHAR(30) NOT NULL,
    active      BOOLEAN     NOT NULL DEFAULT TRUE,
    starts_on   DATE        NOT NULL,
    expires_on  DATE        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

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

CREATE TABLE IF NOT EXISTS warranty_claims
(
    id             VARCHAR(40) PRIMARY KEY,
    warranty_id    VARCHAR(30) NOT NULL,
    customer_id    VARCHAR(11) NOT NULL,
    description    TEXT        NOT NULL,
    status         VARCHAR(30) NOT NULL DEFAULT 'OPEN',
    requires_human BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

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

CREATE TABLE IF NOT EXISTS kb_chunks
(
    id         BIGSERIAL PRIMARY KEY,
    source     VARCHAR(255) NOT NULL,
    title      VARCHAR(255) NOT NULL,
    content    TEXT         NOT NULL,
    metadata   JSONB        NOT NULL DEFAULT '{}'::jsonb,
    embedding  VECTOR(1536)          DEFAULT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- TRIGGERS updated_at
-- =========================================================

CREATE OR REPLACE TRIGGER trg_orders_updated_at
    BEFORE UPDATE
    ON orders
    FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE TRIGGER trg_warranty_claims_updated_at
    BEFORE UPDATE
    ON warranty_claims
    FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- =========================================================
-- ÍNDICES
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_products_category ON products (category);
CREATE INDEX IF NOT EXISTS idx_products_price ON products (price);
CREATE INDEX IF NOT EXISTS idx_products_specs ON products USING GIN (specs);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items (order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items (product_sku);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status);
CREATE INDEX IF NOT EXISTS idx_warranties_order ON warranties (order_id);
CREATE INDEX IF NOT EXISTS idx_warranties_product ON warranties (product_sku);
CREATE INDEX IF NOT EXISTS idx_claims_customer ON warranty_claims (customer_id);

-- El índice vectorial se crea después de insertar los embeddings:
-- CREATE INDEX idx_kb_chunks_embedding
--     ON kb_chunks USING hnsw (embedding vector_cosine_ops);

-- =========================================================
-- PRODUCTOS: 54 REGISTROS
-- Categorías: LAPTOP, TELEVISION, CELULAR, ACCESSORY, TABLET, AUDIO, GAMING
-- =========================================================

INSERT INTO products (sku, name, category, description, price, stock, specs)
VALUES

-- -------------------------
-- LAPTOPS (14)
-- -------------------------
('LAP-DES-001',
 'ASUS Vivobook Pro 15 OLED',
 'LAPTOP',
 'Portátil recomendado para diseño gráfico y creación de contenido.',
 4799900, 8,
 '{
   "processor": "AMD Ryzen 7",
   "ram_gb": 16,
   "storage": "1 TB SSD",
   "gpu": "NVIDIA RTX 3050 6 GB",
   "display": "15.6 OLED",
   "resolution": "2.8K",
   "recommended_for": [
     "diseño gráfico",
     "fotografía",
     "edición de video"
   ]
 }'::jsonb),
('LAP-DES-002',
 'Lenovo LOQ 15',
 'LAPTOP',
 'Portátil de alto rendimiento con tarjeta gráfica dedicada.',
 4499900, 5,
 '{
   "processor": "Intel Core i5",
   "ram_gb": 16,
   "storage": "512 GB SSD",
   "gpu": "NVIDIA RTX 4050 6 GB",
   "display": "15.6 IPS",
   "resolution": "Full HD",
   "recommended_for": [
     "diseño gráfico",
     "modelado 3D",
     "gaming"
   ]
 }'::jsonb),
('LAP-DES-003',
 'Acer Swift Go 14 OLED',
 'LAPTOP',
 'Portátil liviano con pantalla OLED para trabajo creativo.',
 3999900, 6,
 '{
   "processor": "Intel Core Ultra 5",
   "ram_gb": 16,
   "storage": "512 GB SSD",
   "gpu": "Intel Arc integrada",
   "display": "14 OLED",
   "resolution": "2.8K",
   "recommended_for": [
     "diseño gráfico",
     "ilustración",
     "movilidad"
   ]
 }'::jsonb),
('LAP-OFF-001',
 'HP Pavilion 15',
 'LAPTOP',
 'Portátil para productividad, estudio y tareas de oficina.',
 2899900, 10,
 '{
   "processor": "Intel Core i5",
   "ram_gb": 8,
   "storage": "512 GB SSD",
   "gpu": "Intel Iris Xe",
   "display": "15.6 IPS",
   "resolution": "Full HD",
   "recommended_for": [
     "oficina",
     "estudio",
     "navegación"
   ]
 }'::jsonb),
('LAP-PRO-001',
 'MacBook Pro 14',
 'LAPTOP',
 'Equipo profesional para diseño y edición audiovisual.',
 8999900, 3,
 '{
   "processor": "Apple M3 Pro",
   "ram_gb": 18,
   "storage": "512 GB SSD",
   "gpu": "GPU integrada Apple",
   "display": "14.2 Liquid Retina XDR",
   "resolution": "3024x1964",
   "recommended_for": [
     "diseño profesional",
     "edición de video",
     "producción"
   ]
 }'::jsonb),
('LAP-PRO-002',
 'MacBook Air 13 M3',
 'LAPTOP',
 'Portátil ultraligero de Apple con chip M3, ideal para profesionales en movimiento.',
 6499900, 7,
 '{
   "processor": "Apple M3",
   "ram_gb": 8,
   "storage": "256 GB SSD",
   "gpu": "GPU integrada Apple 8 núcleos",
   "display": "13.6 Liquid Retina",
   "resolution": "2560x1664",
   "recommended_for": [
     "productividad",
     "desarrollo",
     "movilidad"
   ]
 }'::jsonb),
('LAP-GAM-001',
 'ASUS ROG Strix G16',
 'LAPTOP',
 'Portátil gaming de alta gama con pantalla de 165 Hz.',
 7299900, 4,
 '{
   "processor": "Intel Core i7 13650HX",
   "ram_gb": 16,
   "storage": "1 TB SSD",
   "gpu": "NVIDIA RTX 4060 8 GB",
   "display": "16 IPS",
   "resolution": "Full HD",
   "refresh_rate_hz": 165,
   "recommended_for": [
     "gaming",
     "streaming",
     "renderizado"
   ]
 }'::jsonb),
('LAP-GAM-002',
 'Lenovo Legion 5 Pro',
 'LAPTOP',
 'Portátil gaming con pantalla QHD de 165 Hz y refrigeración avanzada.',
 6799900, 3,
 '{
   "processor": "AMD Ryzen 7 7745HX",
   "ram_gb": 16,
   "storage": "512 GB SSD",
   "gpu": "NVIDIA RTX 4060 8 GB",
   "display": "16 IPS QHD",
   "resolution": "2560x1600",
   "refresh_rate_hz": 165,
   "recommended_for": [
     "gaming",
     "diseño 3D"
   ]
 }'::jsonb),
('LAP-GAM-003',
 'MSI Katana 15',
 'LAPTOP',
 'Portátil gaming de entrada con buena relación precio-rendimiento.',
 3799900, 6,
 '{
   "processor": "Intel Core i7 12650H",
   "ram_gb": 8,
   "storage": "512 GB SSD",
   "gpu": "NVIDIA RTX 4050 6 GB",
   "display": "15.6 IPS",
   "resolution": "Full HD",
   "refresh_rate_hz": 144,
   "recommended_for": [
     "gaming",
     "estudio"
   ]
 }'::jsonb),
('LAP-OFF-002',
 'Dell Inspiron 15',
 'LAPTOP',
 'Portátil versátil para el hogar y la oficina.',
 2499900, 12,
 '{
   "processor": "Intel Core i3 1305U",
   "ram_gb": 8,
   "storage": "256 GB SSD",
   "gpu": "Intel UHD",
   "display": "15.6 TN",
   "resolution": "Full HD",
   "recommended_for": [
     "hogar",
     "oficina",
     "estudio básico"
   ]
 }'::jsonb),
('LAP-OFF-003',
 'Lenovo IdeaPad Slim 3',
 'LAPTOP',
 'Portátil económico para tareas cotidianas y navegación.',
 1899900, 15,
 '{
   "processor": "AMD Ryzen 5 7520U",
   "ram_gb": 8,
   "storage": "256 GB SSD",
   "gpu": "AMD Radeon integrada",
   "display": "15.6 TN",
   "resolution": "Full HD",
   "recommended_for": [
     "hogar",
     "estudio",
     "presupuesto"
   ]
 }'::jsonb),
('LAP-OFF-004',
 'HP 250 G9',
 'LAPTOP',
 'Portátil empresarial confiable para trabajo diario.',
 2199900, 9,
 '{
   "processor": "Intel Core i5 1235U",
   "ram_gb": 8,
   "storage": "512 GB SSD",
   "gpu": "Intel Iris Xe",
   "display": "15.6 IPS",
   "resolution": "Full HD",
   "recommended_for": [
     "empresarial",
     "oficina"
   ]
 }'::jsonb),
('LAP-DES-004',
 'ASUS ProArt Studiobook 16',
 'LAPTOP',
 'Estación de trabajo portátil para artistas y creadores profesionales.',
 9499900, 2,
 '{
   "processor": "AMD Ryzen 9 7945HX",
   "ram_gb": 32,
   "storage": "1 TB SSD",
   "gpu": "NVIDIA RTX 4070 8 GB",
   "display": "16 OLED",
   "resolution": "3.2K",
   "recommended_for": [
     "diseño profesional",
     "animación 3D",
     "producción audiovisual"
   ]
 }'::jsonb),
('LAP-PRO-003',
 'MacBook Pro 16 M3 Max',
 'LAPTOP',
 'El portátil más potente de Apple para producción profesional exigente.',
 14999900, 2,
 '{
   "processor": "Apple M3 Max",
   "ram_gb": 36,
   "storage": "1 TB SSD",
   "gpu": "GPU integrada Apple 40 núcleos",
   "display": "16.2 Liquid Retina XDR",
   "resolution": "3456x2234",
   "recommended_for": [
     "edición de video 8K",
     "desarrollo avanzado",
     "producción musical"
   ]
 }'::jsonb),

-- -------------------------
-- TELEVISORES (10)
-- -------------------------
('TV-LG-001',
 'LG OLED evo 55 pulgadas C3',
 'TELEVISION',
 'Televisor OLED 4K con funciones inteligentes y Dolby Vision.',
 4299900, 4,
 '{
   "size_inches": 55,
   "resolution": "4K",
   "panel": "OLED",
   "operating_system": "webOS",
   "hdmi_ports": 4,
   "dolby_vision": true,
   "dolby_atmos": true
 }'::jsonb),
('TV-LG-002',
 'LG OLED evo 65 pulgadas C3',
 'TELEVISION',
 'Televisor OLED 4K de 65 pulgadas con procesador α9 Gen6.',
 6499900, 2,
 '{
   "size_inches": 65,
   "resolution": "4K",
   "panel": "OLED",
   "operating_system": "webOS",
   "hdmi_ports": 4,
   "dolby_vision": true,
   "dolby_atmos": true
 }'::jsonb),
('TV-LG-003',
 'LG NanoCell 50 pulgadas',
 'TELEVISION',
 'Televisor 4K con tecnología NanoCell para colores más precisos.',
 1999900, 6,
 '{
   "size_inches": 50,
   "resolution": "4K",
   "panel": "NanoCell",
   "operating_system": "webOS",
   "hdmi_ports": 3
 }'::jsonb),
('TV-SAM-001',
 'Samsung Crystal UHD 55 pulgadas',
 'TELEVISION',
 'Televisor inteligente 4K para entretenimiento en el hogar.',
 2399900, 7,
 '{
   "size_inches": 55,
   "resolution": "4K",
   "panel": "LED",
   "operating_system": "Tizen",
   "hdmi_ports": 3
 }'::jsonb),
('TV-SAM-002',
 'Samsung Neo QLED 65 pulgadas QN85B',
 'TELEVISION',
 'Televisor Neo QLED con Mini LED y procesador Neural Quantum.',
 7999900, 2,
 '{
   "size_inches": 65,
   "resolution": "4K",
   "panel": "Neo QLED",
   "operating_system": "Tizen",
   "hdmi_ports": 4,
   "refresh_rate_hz": 120,
   "dolby_atmos": true
 }'::jsonb),
('TV-SAM-003',
 'Samsung The Frame 55 pulgadas',
 'TELEVISION',
 'Televisor que luce como un cuadro cuando no está en uso. Modo Arte incluido.',
 3899900, 3,
 '{
   "size_inches": 55,
   "resolution": "4K",
   "panel": "QLED",
   "operating_system": "Tizen",
   "hdmi_ports": 3,
   "art_mode": true
 }'::jsonb),
('TV-TCL-001',
 'TCL QLED 50 pulgadas C645',
 'TELEVISION',
 'Televisor QLED con Google TV y Dolby Vision.',
 1999900, 0,
 '{
   "size_inches": 50,
   "resolution": "4K",
   "panel": "QLED",
   "operating_system": "Google TV",
   "hdmi_ports": 3,
   "dolby_vision": true
 }'::jsonb),
('TV-TCL-002',
 'TCL LED 43 pulgadas S5400A',
 'TELEVISION',
 'Televisor económico con Android TV y acceso a apps de streaming.',
 1099900, 10,
 '{
   "size_inches": 43,
   "resolution": "Full HD",
   "panel": "LED",
   "operating_system": "Android TV",
   "hdmi_ports": 2
 }'::jsonb),
('TV-SON-001',
 'Sony Bravia XR 55 pulgadas X90L',
 'TELEVISION',
 'Televisor LED 4K con procesador cognitivo XR y Google TV.',
 4599900, 3,
 '{
   "size_inches": 55,
   "resolution": "4K",
   "panel": "LED",
   "operating_system": "Google TV",
   "hdmi_ports": 4,
   "refresh_rate_hz": 120,
   "dolby_vision": true,
   "dolby_atmos": true
 }'::jsonb),
('TV-SON-002',
 'Sony Bravia OLED 55 pulgadas A80L',
 'TELEVISION',
 'Televisor OLED 4K Sony con Acoustic Surface Audio.',
 6299900, 2,
 '{
   "size_inches": 55,
   "resolution": "4K",
   "panel": "OLED",
   "operating_system": "Google TV",
   "hdmi_ports": 4,
   "dolby_vision": true,
   "dolby_atmos": true
 }'::jsonb),

-- -------------------------
-- CELULARES (12)
-- -------------------------
('CEL-SAM-001',
 'Samsung Galaxy S24',
 'CELULAR',
 'Celular de gama alta con cámara avanzada e inteligencia artificial integrada.',
 3899900, 12,
 '{
   "storage": "256 GB",
   "ram_gb": 8,
   "display": "6.2 AMOLED",
   "camera": "50 MP",
   "network": "5G",
   "os": "Android 14"
 }'::jsonb),
('CEL-SAM-002',
 'Samsung Galaxy S24 Ultra',
 'CELULAR',
 'El Samsung más potente con S Pen integrado y cámara de 200 MP.',
 6499900, 5,
 '{
   "storage": "256 GB",
   "ram_gb": 12,
   "display": "6.8 AMOLED Dynamic LTPO",
   "camera": "200 MP",
   "network": "5G",
   "s_pen": true,
   "os": "Android 14"
 }'::jsonb),
('CEL-SAM-003',
 'Samsung Galaxy A55',
 'CELULAR',
 'Gama media premium con diseño robusto y cámara versátil.',
 1899900, 18,
 '{
   "storage": "128 GB",
   "ram_gb": 8,
   "display": "6.6 AMOLED",
   "camera": "50 MP",
   "network": "5G",
   "os": "Android 14"
 }'::jsonb),
('CEL-SAM-004',
 'Samsung Galaxy A35',
 'CELULAR',
 'Celular de gama media con pantalla AMOLED y batería duradera.',
 1399900, 20,
 '{
   "storage": "128 GB",
   "ram_gb": 6,
   "display": "6.6 AMOLED",
   "camera": "50 MP",
   "network": "4G",
   "os": "Android 14"
 }'::jsonb),
('CEL-XIA-001',
 'Xiaomi Redmi Note 13 Pro',
 'CELULAR',
 'Celular de gama media con cámara de 200 MP y carga rápida de 67 W.',
 1599900, 15,
 '{
   "storage": "256 GB",
   "ram_gb": 8,
   "display": "6.67 AMOLED",
   "camera": "200 MP",
   "network": "5G",
   "charging_w": 67,
   "os": "Android 13"
 }'::jsonb),
('CEL-XIA-002',
 'Xiaomi 14',
 'CELULAR',
 'Flagship de Xiaomi con cámara Leica y procesador Snapdragon 8 Gen 3.',
 4299900, 6,
 '{
   "storage": "256 GB",
   "ram_gb": 12,
   "display": "6.36 AMOLED",
   "camera": "50 MP Leica",
   "network": "5G",
   "charging_w": 90,
   "os": "Android 14"
 }'::jsonb),
('CEL-XIA-003',
 'Xiaomi Redmi 13C',
 'CELULAR',
 'Celular de entrada con buena batería y pantalla grande.',
 699900, 25,
 '{
   "storage": "128 GB",
   "ram_gb": 4,
   "display": "6.74 IPS",
   "camera": "50 MP",
   "network": "4G",
   "charging_w": 18,
   "os": "Android 13"
 }'::jsonb),
('CEL-APL-001',
 'Apple iPhone 15',
 'CELULAR',
 'iPhone con chip A16 Bionic, Dynamic Island y cámara de 48 MP.',
 4499900, 8,
 '{
   "storage": "128 GB",
   "display": "6.1 Super Retina XDR",
   "camera": "48 MP",
   "network": "5G",
   "chip": "A16 Bionic",
   "os": "iOS 17"
 }'::jsonb),
('CEL-APL-002',
 'Apple iPhone 15 Pro',
 'CELULAR',
 'iPhone Pro con titanio, chip A17 Pro y cámara de 48 MP con zoom 5x.',
 6499900, 5,
 '{
   "storage": "256 GB",
   "display": "6.1 Super Retina XDR",
   "camera": "48 MP",
   "network": "5G",
   "chip": "A17 Pro",
   "material": "titanio",
   "os": "iOS 17"
 }'::jsonb),
('CEL-MOT-001',
 'Motorola Edge 50 Pro',
 'CELULAR',
 'Celular con carga inalámbrica de 50 W y pantalla pOLED de 144 Hz.',
 2199900, 10,
 '{
   "storage": "256 GB",
   "ram_gb": 12,
   "display": "6.7 pOLED",
   "camera": "50 MP",
   "network": "5G",
   "charging_w": 125,
   "wireless_charging_w": 50,
   "os": "Android 14"
 }'::jsonb),
('CEL-MOT-002',
 'Motorola Moto G84',
 'CELULAR',
 'Gama media con pantalla pOLED de 120 Hz y altavoces estéreo.',
 1099900, 14,
 '{
   "storage": "256 GB",
   "ram_gb": 12,
   "display": "6.55 pOLED",
   "camera": "50 MP",
   "network": "4G",
   "charging_w": 33,
   "os": "Android 13"
 }'::jsonb),
('CEL-NOK-001',
 'Nokia G42',
 'CELULAR',
 'Celular con diseño reparable y garantía extendida de 3 años.',
 799900, 8,
 '{
   "storage": "128 GB",
   "ram_gb": 6,
   "display": "6.56 IPS",
   "camera": "50 MP",
   "network": "5G",
   "repearable": true,
   "os": "Android 13"
 }'::jsonb),

-- -------------------------
-- TABLETS (6)
-- -------------------------
('TAB-SAM-001',
 'Samsung Galaxy Tab S9 FE',
 'TABLET',
 'Tablet premium con pantalla TFT de 10.9 pulgadas y S Pen incluido.',
 1799900, 7,
 '{
   "storage": "128 GB",
   "ram_gb": 6,
   "display": "10.9 TFT",
   "camera": "8 MP",
   "network": "Wi-Fi",
   "s_pen": true,
   "os": "Android 13"
 }'::jsonb),
('TAB-SAM-002',
 'Samsung Galaxy Tab A9+',
 'TABLET',
 'Tablet familiar con pantalla grande y sonido Dolby Atmos.',
 1299900, 10,
 '{
   "storage": "64 GB",
   "ram_gb": 4,
   "display": "11 IPS",
   "camera": "8 MP",
   "network": "Wi-Fi",
   "dolby_atmos": true,
   "os": "Android 13"
 }'::jsonb),
('TAB-APL-001',
 'Apple iPad 10.9 Gen 10',
 'TABLET',
 'iPad con chip A14 Bionic, compatible con Apple Pencil de primera generación.',
 2199900, 5,
 '{
   "storage": "64 GB",
   "display": "10.9 Liquid Retina",
   "camera": "12 MP",
   "network": "Wi-Fi",
   "chip": "A14 Bionic",
   "os": "iPadOS 17"
 }'::jsonb),
('TAB-APL-002',
 'Apple iPad Pro 11 M4',
 'TABLET',
 'El iPad más potente con chip M4 y pantalla Ultra Retina XDR OLED.',
 5999900, 3,
 '{
   "storage": "256 GB",
   "display": "11 Ultra Retina XDR OLED",
   "camera": "12 MP",
   "network": "Wi-Fi",
   "chip": "M4",
   "os": "iPadOS 17"
 }'::jsonb),
('TAB-LEN-001',
 'Lenovo Tab P12',
 'TABLET',
 'Tablet de 12.7 pulgadas con pantalla 3K y soporte para lápiz óptico.',
 1499900, 6,
 '{
   "storage": "128 GB",
   "ram_gb": 8,
   "display": "12.7 IPS 3K",
   "camera": "13 MP",
   "network": "Wi-Fi",
   "stylus_support": true,
   "os": "Android 13"
 }'::jsonb),
('TAB-XIA-001',
 'Xiaomi Pad 6',
 'TABLET',
 'Tablet con procesador Snapdragon 870 y pantalla de 144 Hz.',
 1299900, 8,
 '{
   "storage": "128 GB",
   "ram_gb": 6,
   "display": "11 IPS",
   "resolution": "2880x1800",
   "refresh_rate_hz": 144,
   "camera": "13 MP",
   "network": "Wi-Fi",
   "os": "Android 13"
 }'::jsonb),

-- -------------------------
-- AUDIO (6)
-- -------------------------
('AUD-SON-001',
 'Sony WH-1000XM5',
 'AUDIO',
 'Audífonos over-ear con cancelación de ruido líder de la industria.',
 1599900, 10,
 '{
   "type": "over-ear",
   "noise_cancelling": true,
   "battery_hours": 30,
   "connection": [
     "Bluetooth 5.2",
     "USB-C"
   ],
   "foldable": false
 }'::jsonb),
('AUD-SON-002',
 'Sony WF-1000XM5',
 'AUDIO',
 'Audífonos in-ear con la mejor cancelación de ruido en formato TWS.',
 1099900, 12,
 '{
   "type": "in-ear TWS",
   "noise_cancelling": true,
   "battery_hours": 8,
   "case_battery_hours": 24,
   "connection": [
     "Bluetooth 5.3"
   ]
 }'::jsonb),
('AUD-APL-001',
 'Apple AirPods Pro Gen 2',
 'AUDIO',
 'Audífonos TWS de Apple con cancelación de ruido adaptativa y Audio Espacial.',
 1399900, 9,
 '{
   "type": "in-ear TWS",
   "noise_cancelling": true,
   "battery_hours": 6,
   "case_battery_hours": 30,
   "connection": [
     "Bluetooth 5.3"
   ],
   "spatial_audio": true
 }'::jsonb),
('AUD-JBL-001',
 'JBL Tune 770NC',
 'AUDIO',
 'Audífonos over-ear inalámbricos con cancelación de ruido adaptativa.',
 499900, 15,
 '{
   "type": "over-ear",
   "noise_cancelling": true,
   "battery_hours": 70,
   "connection": [
     "Bluetooth 5.3",
     "AUX"
   ],
   "foldable": true
 }'::jsonb),
('AUD-JBL-002',
 'JBL Flip 6',
 'AUDIO',
 'Parlante Bluetooth portátil resistente al agua con sonido potente.',
 449900, 20,
 '{
   "type": "speaker",
   "waterproof": "IP67",
   "battery_hours": 12,
   "connection": [
     "Bluetooth 5.1"
   ],
   "partyboost": true
 }'::jsonb),
('AUD-BOC-001',
 'Bose QuietComfort 45',
 'AUDIO',
 'Audífonos premium con cancelación de ruido y comodidad excepcional.',
 1299900, 6,
 '{
   "type": "over-ear",
   "noise_cancelling": true,
   "battery_hours": 24,
   "connection": [
     "Bluetooth 5.1",
     "AUX"
   ],
   "foldable": true
 }'::jsonb),

-- -------------------------
-- GAMING (6)
-- -------------------------
('GAM-SON-001',
 'PlayStation 5 Slim',
 'GAMING',
 'Consola de nueva generación con lector de disco y SSD ultra rápido.',
 2699900, 5,
 '{
   "storage": "1 TB SSD",
   "resolution": "4K",
   "fps": 120,
   "ray_tracing": true,
   "backward_compatible": true
 }'::jsonb),
('GAM-SON-002',
 'DualSense PlayStation 5',
 'GAMING',
 'Control inalámbrico con gatillos adaptativos y retroalimentación háptica.',
 399900, 15,
 '{
   "connection": [
     "Bluetooth",
     "USB-C"
   ],
   "battery_hours": 12,
   "haptic_feedback": true,
   "adaptive_triggers": true
 }'::jsonb),
('GAM-MSF-001',
 'Xbox Series X',
 'GAMING',
 'Consola Xbox de mayor rendimiento con 12 teraflops y 1 TB SSD.',
 2799900, 4,
 '{
   "storage": "1 TB SSD",
   "resolution": "4K",
   "fps": 120,
   "ray_tracing": true,
   "quick_resume": true
 }'::jsonb),
('GAM-NIN-001',
 'Nintendo Switch OLED',
 'GAMING',
 'Consola híbrida con pantalla OLED de 7 pulgadas y modo portátil.',
 1799900, 8,
 '{
   "storage": "64 GB",
   "display": "7 OLED",
   "modes": [
     "TV",
     "mesa",
     "portátil"
   ],
   "battery_hours": 9
 }'::jsonb),
('GAM-LOG-001',
 'Logitech G Pro X Superlight 2',
 'GAMING',
 'Mouse gaming ultraliviano con sensor HERO 2 y 95 horas de batería.',
 649900, 10,
 '{
   "weight_g": 60,
   "sensor": "HERO 2",
   "dpi": 32000,
   "battery_hours": 95,
   "connection": [
     "Bluetooth",
     "USB dongle"
   ]
 }'::jsonb),
('GAM-LOG-002',
 'Logitech G915 TKL',
 'GAMING',
 'Teclado mecánico inalámbrico delgado para gaming y productividad.',
 899900, 7,
 '{
   "connection": [
     "Bluetooth",
     "USB dongle"
   ],
   "switch_type": "GL Táctil",
   "battery_hours": 40,
   "rgb": true,
   "tenkeyless": true
 }'::jsonb),

-- -------------------------
-- ACCESORIOS (10)
-- -------------------------
('ACC-MON-001',
 'Monitor LG UltraGear 27 QHD',
 'ACCESSORY',
 'Monitor IPS de 165 Hz con resolución QHD para trabajo y gaming.',
 1399900, 9,
 '{
   "size_inches": 27,
   "resolution": "QHD",
   "panel": "IPS",
   "refresh_rate_hz": 165,
   "response_ms": 1,
   "hdr": true
 }'::jsonb),
('ACC-MON-002',
 'Monitor Samsung 32 4K',
 'ACCESSORY',
 'Monitor 4K UHD de 32 pulgadas ideal para diseño y productividad.',
 1699900, 6,
 '{
   "size_inches": 32,
   "resolution": "4K",
   "panel": "IPS",
   "refresh_rate_hz": 60,
   "hdr": true,
   "usb_c": true
 }'::jsonb),
('ACC-MON-003',
 'Monitor ASUS ProArt 27 OLED',
 'ACCESSORY',
 'Monitor OLED profesional con cobertura del 99% de DCI-P3.',
 3499900, 3,
 '{
   "size_inches": 27,
   "resolution": "QHD",
   "panel": "OLED",
   "refresh_rate_hz": 240,
   "response_ms": 0.1,
   "dci_p3_pct": 99
 }'::jsonb),
('ACC-MOU-001',
 'Mouse Logitech MX Master 3S',
 'ACCESSORY',
 'Mouse inalámbrico ergonómico con scroll MagSpeed para productividad.',
 449900, 20,
 '{
   "connection": [
     "Bluetooth",
     "USB dongle"
   ],
   "wireless": true,
   "dpi": 8000,
   "recommended_for": [
     "diseño",
     "productividad"
   ]
 }'::jsonb),
('ACC-MOU-002',
 'Mouse Apple Magic Mouse',
 'ACCESSORY',
 'Mouse inalámbrico de Apple con superficie táctil y diseño minimalista.',
 399900, 8,
 '{
   "connection": [
     "Bluetooth"
   ],
   "wireless": true,
   "touch_surface": true,
   "recommended_for": [
     "Mac",
     "productividad"
   ]
 }'::jsonb),
('ACC-KEY-001',
 'Teclado Logitech MX Keys S',
 'ACCESSORY',
 'Teclado inalámbrico con retroiluminación adaptativa y teclas de flujo.',
 599900, 12,
 '{
   "connection": [
     "Bluetooth",
     "USB dongle"
   ],
   "wireless": true,
   "backlit": true,
   "recommended_for": [
     "productividad",
     "oficina"
   ]
 }'::jsonb),
('ACC-KEY-002',
 'Teclado Apple Magic Keyboard con Touch ID',
 'ACCESSORY',
 'Teclado compacto de Apple con Touch ID para autenticación segura.',
 549900, 7,
 '{
   "connection": [
     "Bluetooth"
   ],
   "wireless": true,
   "touch_id": true,
   "recommended_for": [
     "Mac",
     "oficina"
   ]
 }'::jsonb),
('ACC-CAR-001',
 'Cargador USB-C 65W Anker',
 'ACCESSORY',
 'Cargador compacto de pared con tecnología GaN y dos puertos.',
 129900, 30,
 '{
   "power_w": 65,
   "ports": 2,
   "gan_technology": true,
   "compatible_with": [
     "laptop",
     "celular",
     "tablet"
   ]
 }'::jsonb),
('ACC-HUB-001',
 'Hub USB-C 7 en 1 Anker',
 'ACCESSORY',
 'Hub multipuerto con HDMI 4K, lector de tarjetas y carga de 100 W.',
 219900, 18,
 '{
   "ports": 7,
   "hdmi": "4K",
   "card_reader": true,
   "power_delivery_w": 100,
   "usb_a_ports": 3
 }'::jsonb),
('ACC-WEB-001',
 'Webcam Logitech C920s HD Pro',
 'ACCESSORY',
 'Webcam Full HD con obturador de privacidad para videollamadas profesionales.',
 349900, 14,
 '{
   "resolution": "1080p",
   "fps": 30,
   "autofocus": true,
   "privacy_shutter": true,
   "connection": "USB-A"
 }'::jsonb)

ON CONFLICT (sku) DO NOTHING;

-- =========================================================
-- CLIENTES (10)
-- =========================================================

INSERT INTO customers (identification, full_name, phone, email, kind)
VALUES ('1020304050', 'María Gómez', '3001234567', 'maria.gomez@example.com', 'FREQUENT'),
       ('987654321', 'Carlos Rodríguez', '3109876543', 'carlos.rodriguez@example.com', 'FREQUENT'),
       ('456789123', 'Laura Martínez', '6012345678', 'laura.martinez@example.com', 'FREQUENT'),
       ('1234567890', 'Andrés Pérez', '3204567890', 'andres.perez@example.com', 'FREQUENT'),
       ('98765432', 'Valentina Torres', '3157654321', 'valentina.torres@example.com', 'NEW'),
       ('11223344', 'Santiago Herrera', '3012233445', 'santiago.herrera@example.com', 'FREQUENT'),
       ('55667788', 'Daniela Vargas', '3045566778', 'daniela.vargas@example.com', 'NEW'),
       ('99001122', 'Felipe Moreno', '3199001122', 'felipe.moreno@example.com', 'FREQUENT'),
       ('33445566', 'Camila Ospina', '6033445566', 'camila.ospina@example.com', 'FREQUENT'),
       ('77889900', 'Sebastián Ríos', '3177889900', 'sebastian.rios@example.com', 'NEW')
ON CONFLICT (identification) DO NOTHING;

-- =========================================================
-- PEDIDOS (15)
-- =========================================================

INSERT INTO orders (id, customer_id, status, estimated_delivery, address)
VALUES ('ORD-1001', '1020304050', 'IN_TRANSIT', CURRENT_DATE + 2, 'Carrera 43A # 10-25, Medellín'),
       ('ORD-1002', '987654321', 'DELIVERED', CURRENT_DATE - 30, 'Calle 100 # 15-40, Bogotá'),
       ('ORD-1003', '456789123', 'PREPARING', CURRENT_DATE + 5, 'Avenida 6N # 24-30, Cali'),
       ('ORD-1004', '1234567890', 'SHIPPED', CURRENT_DATE + 3, 'Carrera 53 # 80-67, Barranquilla'),
       ('ORD-1005', '1020304050', 'CANCELLED', NULL, 'Carrera 43A # 10-25, Medellín'),
       ('ORD-1006', '98765432', 'CONFIRMED', CURRENT_DATE + 7, 'Calle 15 # 28-40, Manizales'),
       ('ORD-1007', '11223344', 'DELIVERED', CURRENT_DATE - 60, 'Carrera 70 # 45-10, Medellín'),
       ('ORD-1008', '55667788', 'IN_TRANSIT', CURRENT_DATE + 1,
        'Avenida El Dorado # 90-21, Bogotá'),
       ('ORD-1009', '99001122', 'DELIVERED', CURRENT_DATE - 15, 'Calle 5 # 40-30, Cali'),
       ('ORD-1010', '33445566', 'PREPARING', CURRENT_DATE + 4, 'Carrera 8 # 15-20, Pereira'),
       ('ORD-1011', '77889900', 'CONFIRMED', CURRENT_DATE + 6, 'Calle 72 # 10-35, Bogotá'),
       ('ORD-1012', '1020304050', 'DELIVERED', CURRENT_DATE - 90, 'Carrera 43A # 10-25, Medellín'),
       ('ORD-1013', '987654321', 'SHIPPED', CURRENT_DATE + 2, 'Calle 100 # 15-40, Bogotá'),
       ('ORD-1014', '456789123', 'CANCELLED', NULL, 'Avenida 6N # 24-30, Cali'),
       ('ORD-1015', '11223344', 'IN_TRANSIT', CURRENT_DATE + 1, 'Carrera 70 # 45-10, Medellín')
ON CONFLICT (id) DO NOTHING;

-- =========================================================
-- LÍNEAS DE PEDIDO
-- =========================================================

INSERT INTO order_items (order_id, product_sku, quantity, unit_price)
VALUES ('ORD-1001', 'LAP-DES-001', 1, 4799900),
       ('ORD-1002', 'TV-LG-001', 1, 4299900),
       ('ORD-1002', 'AUD-SON-001', 1, 1599900),
       ('ORD-1003', 'CEL-SAM-001', 1, 3899900),
       ('ORD-1004', 'CEL-XIA-001', 1, 1599900),
       ('ORD-1004', 'ACC-CAR-001', 1, 129900),
       ('ORD-1005', 'ACC-MON-001', 1, 1399900),
       ('ORD-1006', 'TAB-SAM-001', 1, 1799900),
       ('ORD-1007', 'LAP-PRO-001', 1, 8999900),
       ('ORD-1007', 'ACC-MOU-001', 1, 449900),
       ('ORD-1008', 'CEL-APL-001', 1, 4499900),
       ('ORD-1008', 'AUD-APL-001', 1, 1399900),
       ('ORD-1009', 'GAM-SON-001', 1, 2699900),
       ('ORD-1009', 'GAM-SON-002', 2, 399900),
       ('ORD-1010', 'TV-SAM-001', 1, 2399900),
       ('ORD-1011', 'LAP-GAM-001', 1, 7299900),
       ('ORD-1012', 'CEL-SAM-002', 1, 6499900),
       ('ORD-1012', 'ACC-HUB-001', 1, 219900),
       ('ORD-1013', 'TV-SON-001', 1, 4599900),
       ('ORD-1014', 'TAB-APL-001', 1, 2199900),
       ('ORD-1015', 'LAP-OFF-001', 1, 2899900),
       ('ORD-1015', 'ACC-KEY-001', 1, 599900),
       ('ORD-1015', 'ACC-WEB-001', 1, 349900)
ON CONFLICT (order_id, product_sku) DO NOTHING;

-- =========================================================
-- GARANTÍAS (12)
-- =========================================================

INSERT INTO warranties (id, product_sku, order_id, active, starts_on, expires_on)
VALUES
-- Vigentes
('WAR-1001', 'TV-LG-001', 'ORD-1002', TRUE, CURRENT_DATE - 180, CURRENT_DATE + 185),
('WAR-1002', 'LAP-DES-001', 'ORD-1001', TRUE, CURRENT_DATE - 90, CURRENT_DATE + 275),
('WAR-1003', 'AUD-SON-001', 'ORD-1002', TRUE, CURRENT_DATE - 180, CURRENT_DATE + 185),
('WAR-1004', 'CEL-SAM-001', 'ORD-1003', TRUE, CURRENT_DATE - 10, CURRENT_DATE + 355),
('WAR-1005', 'TAB-SAM-001', 'ORD-1006', TRUE, CURRENT_DATE, CURRENT_DATE + 365),
('WAR-1006', 'LAP-PRO-001', 'ORD-1007', TRUE, CURRENT_DATE - 60, CURRENT_DATE + 305),
('WAR-1007', 'CEL-APL-001', 'ORD-1008', TRUE, CURRENT_DATE - 5, CURRENT_DATE + 360),
('WAR-1008', 'GAM-SON-001', 'ORD-1009', TRUE, CURRENT_DATE - 15, CURRENT_DATE + 350),
('WAR-1009', 'TV-SAM-001', 'ORD-1010', TRUE, CURRENT_DATE, CURRENT_DATE + 365),
('WAR-1010', 'CEL-SAM-002', 'ORD-1012', TRUE, CURRENT_DATE - 90, CURRENT_DATE + 275),
-- Vencidas
('WAR-1011', 'CEL-XIA-001', 'ORD-1004', FALSE, CURRENT_DATE - 730, CURRENT_DATE - 365),
('WAR-1012', 'LAP-GAM-001', 'ORD-1011', FALSE, CURRENT_DATE - 400, CURRENT_DATE - 35)
ON CONFLICT (id) DO NOTHING;

-- =========================================================
-- RECLAMOS DE GARANTÍA (5)
-- =========================================================

INSERT INTO warranty_claims (id, warranty_id, customer_id, description, status, requires_human)
VALUES ('CLM-0001', 'WAR-1001', '987654321',
        'El televisor LG muestra líneas horizontales en la pantalla al encenderse.',
        'IN_REVIEW', FALSE),
       ('CLM-0002', 'WAR-1002', '1020304050',
        'El portátil ASUS se apaga inesperadamente bajo carga moderada.',
        'OPEN', FALSE),
       ('CLM-0003', 'WAR-1006', '11223344',
        'El MacBook Pro no carga correctamente con ninguno de los cables USB-C.',
        'ESCALATED', TRUE),
       ('CLM-0004', 'WAR-1007', '55667788',
        'El iPhone 15 reinicia solo varias veces al día sin motivo aparente.',
        'RESOLVED', FALSE),
       ('CLM-0005', 'WAR-1008', '99001122',
        'El control DualSense tiene drift en el joystick izquierdo.',
        'OPEN', FALSE)
ON CONFLICT (id) DO NOTHING;

-- =========================================================
-- BASE DE CONOCIMIENTO
-- =========================================================

INSERT INTO kb_chunks (source, title, content, metadata)
SELECT 'politica_garantia.md',
       'Condiciones generales de garantía',
       'La garantía cubre defectos de fabricación durante el periodo indicado. No cubre golpes, humedad, manipulación no autorizada o daños causados por fluctuaciones eléctricas.',
       '{
         "category": "warranty",
         "language": "es"
       }'::jsonb
WHERE NOT EXISTS (SELECT 1
                  FROM kb_chunks
                  WHERE source = 'politica_garantia.md'
                    AND title = 'Condiciones generales de garantía');

INSERT INTO kb_chunks (source, title, content, metadata)
SELECT 'politica_devoluciones.md',
       'Política de devoluciones',
       'Las solicitudes de devolución deben registrarse dentro de los cinco días hábiles posteriores a la entrega y el producto debe conservar sus accesorios y empaque.',
       '{
         "category": "returns",
         "language": "es"
       }'::jsonb
WHERE NOT EXISTS (SELECT 1
                  FROM kb_chunks
                  WHERE source = 'politica_devoluciones.md' AND title = 'Política de devoluciones');

INSERT INTO kb_chunks (source, title, content, metadata)
SELECT 'politica_envios.md',
       'Política de envíos',
       'Los envíos a ciudades principales (Bogotá, Medellín, Cali, Barranquilla) tienen un tiempo estimado de 2 a 4 días hábiles. A municipios intermedios el tiempo es de 5 a 8 días hábiles. El envío es gratuito en compras superiores a $200.000 COP.',
       '{
         "category": "shipping",
         "language": "es"
       }'::jsonb
WHERE NOT EXISTS (SELECT 1
                  FROM kb_chunks
                  WHERE source = 'politica_envios.md' AND title = 'Política de envíos');

INSERT INTO kb_chunks (source, title, content, metadata)
SELECT 'faq_garantia.md',
       'Preguntas frecuentes sobre garantía',
       'Para activar una garantía necesitas el número de orden y el SKU del producto. Los reclamos pueden abrirse desde la plataforma o llamando a la línea de soporte. El tiempo de resolución es de 5 a 10 días hábiles según la complejidad del caso.',
       '{
         "category": "warranty",
         "language": "es"
       }'::jsonb
WHERE NOT EXISTS (SELECT 1
                  FROM kb_chunks
                  WHERE source = 'faq_garantia.md'
                    AND title = 'Preguntas frecuentes sobre garantía');

INSERT INTO kb_chunks (source, title, content, metadata)
SELECT 'faq_pedidos.md',
       'Preguntas frecuentes sobre pedidos',
       'Puedes consultar el estado de tu pedido con tu número de orden. Los estados posibles son: CONFIRMED (confirmado), PREPARING (en preparación), SHIPPED (despachado), IN_TRANSIT (en camino), DELIVERED (entregado) y CANCELLED (cancelado). Un pedido cancelado no genera garantía.',
       '{
         "category": "orders",
         "language": "es"
       }'::jsonb
WHERE NOT EXISTS (SELECT 1
                  FROM kb_chunks
                  WHERE source = 'faq_pedidos.md' AND title = 'Preguntas frecuentes sobre pedidos');

COMMIT;