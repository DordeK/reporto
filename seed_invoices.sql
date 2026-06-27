-- =============================================================================
-- Seed script: 1000 random invoices with parties, lines, and tax subtotals
-- Run against the deployed Railway database:
--   psql "$DATABASE_URL" -f seed_invoices.sql
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Raw invoice file placeholder (all seeded invoices share this)
-- ---------------------------------------------------------------------------
INSERT INTO raw_invoice_files (id, source, filename, content, content_hash)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'seed_script',
    'seed_1000_invoices.xml',
    '<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"><cbc:ID>SEED</cbc:ID></Invoice>',
    'seed_script_placeholder_v1_hash_do_not_parse'
)
ON CONFLICT (content_hash) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 2. Supplier parties (20 European companies)
-- ---------------------------------------------------------------------------
INSERT INTO parties (id, name, vat_id, country_code, city_name, postal_zone, street_name, registration_name, company_id, contact_email) VALUES
('a0000000-0000-0000-0000-000000000001', 'Acme Solutions NV',       'BE0401234567', 'BE', 'Brussels',   '1000', 'Rue de la Loi 1',       'Acme Solutions NV',       '0401234567', 'invoices@acme-solutions.be'),
('a0000000-0000-0000-0000-000000000002', 'TechFlow BV',             'NL820123456B01','NL', 'Amsterdam',  '1012', 'Herengracht 420',        'TechFlow BV',             '82012345',  'billing@techflow.nl'),
('a0000000-0000-0000-0000-000000000003', 'Digitech GmbH',           'DE123456789',  'DE', 'Munich',     '80331','Marienplatz 8',          'Digitech GmbH',           'HRB 12345', 'rechnungen@digitech.de'),
('a0000000-0000-0000-0000-000000000004', 'SoftServe SARL',          'FR12345678901','FR', 'Paris',      '75001','Rue de Rivoli 42',       'SoftServe SARL',          '123456789', 'facturation@softserve.fr'),
('a0000000-0000-0000-0000-000000000005', 'Informatika doo',         'SI12345678',   'SI', 'Ljubljana',  '1000', 'Slovenska cesta 55',     'Informatika doo',         '12345678',  'racuni@informatika.si'),
('a0000000-0000-0000-0000-000000000006', 'CloudBase AG',            'CH123456789',  'CH', 'Zurich',     '8001', 'Bahnhofstrasse 10',      'CloudBase AG',            'CHE-123456','invoices@cloudbase.ch'),
('a0000000-0000-0000-0000-000000000007', 'MediaGroup NV',           'BE0502345678', 'BE', 'Antwerp',    '2000', 'Meir 100',              'MediaGroup NV',           '0502345678','finance@mediagroup.be'),
('a0000000-0000-0000-0000-000000000008', 'DataSystems Ltd',         'GB123456789',  'GB', 'London',     'EC1A', '30 Farringdon St',      'DataSystems Ltd',         '12345678',  'accounts@datasystems.co.uk'),
('a0000000-0000-0000-0000-000000000009', 'NordTech AB',             'SE556123456701','SE','Stockholm',  '11120','Kungsgatan 25',          'NordTech AB',             '556123-4567','faktura@nordtech.se'),
('a0000000-0000-0000-0000-000000000010', 'IberSoft SL',             'ES12345678A',  'ES', 'Madrid',     '28001','Gran Via 55',            'IberSoft SL',             'B-12345678','facturas@ibersoft.es'),
('a0000000-0000-0000-0000-000000000011', 'LogiPack NV',             'BE0612345678', 'BE', 'Ghent',      '9000', 'Veldstraat 60',         'LogiPack NV',             '0612345678','accounting@logipack.be'),
('a0000000-0000-0000-0000-000000000012', 'PrintMaster BV',          'NL821234567B01','NL','Rotterdam',  '3011', 'Coolsingel 30',         'PrintMaster BV',          '82123456',  'billing@printmaster.nl'),
('a0000000-0000-0000-0000-000000000013', 'EnergyPlus GmbH',         'DE234567890',  'DE', 'Hamburg',    '20095','Mönckebergstraße 7',    'EnergyPlus GmbH',         'HRB 23456', 'rechnung@energyplus.de'),
('a0000000-0000-0000-0000-000000000014', 'Conseil Pro SARL',        'FR23456789012','FR', 'Lyon',       '69001','Place Bellecour 2',     'Conseil Pro SARL',        '234567890', 'compta@conseilpro.fr'),
('a0000000-0000-0000-0000-000000000015', 'Pametne Rešitve doo',     'SI23456789',   'SI', 'Maribor',    '2000', 'Partizanska cesta 3',   'Pametne Rešitve doo',     '23456789',  'racuni@pametne.si'),
('a0000000-0000-0000-0000-000000000016', 'OfficeSupply SA',         'BE0712345678', 'BE', 'Liège',      '4000', 'Rue Saint-Gilles 10',   'OfficeSupply SA',         '0712345678','finance@officesupply.be'),
('a0000000-0000-0000-0000-000000000017', 'TransEurope NV',          'BE0812345678', 'BE', 'Bruges',     '8000', 'Markt 7',               'TransEurope NV',          '0812345678','billing@transeurope.be'),
('a0000000-0000-0000-0000-000000000018', 'GreenTech BV',            'NL822345678B01','NL','Utrecht',    '3511', 'Oudegracht 100',        'GreenTech BV',            '82234567',  'finance@greentech.nl'),
('a0000000-0000-0000-0000-000000000019', 'Consultare SRL',          'IT12345678901','IT', 'Milan',      '20121','Via Montenapoleone 12', 'Consultare SRL',          'MI-12345',  'fatture@consultare.it'),
('a0000000-0000-0000-0000-000000000020', 'Balkan Tech doo',         'RS123456789',  'RS', 'Belgrade',   '11000','Knez Mihailova 30',     'Balkan Tech doo',         '12345678',  'racun@balkantech.rs')
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 3. Customer parties (5 buyers)
-- ---------------------------------------------------------------------------
INSERT INTO parties (id, name, vat_id, country_code, city_name, postal_zone, street_name, registration_name, company_id, contact_email) VALUES
('b0000000-0000-0000-0000-000000000001', 'Teads SA',                'FR98765432109','FR', 'Paris',      '75008','Avenue des Champs-Élysées 100','Teads SA',             '987654321', 'ap@teads.com'),
('b0000000-0000-0000-0000-000000000002', 'GlobalBuyer NV',          'BE0987654321', 'BE', 'Brussels',   '1050', 'Avenue Louise 200',      'GlobalBuyer NV',          '0987654321','purchase@globalbuyer.be'),
('b0000000-0000-0000-0000-000000000003', 'EuroRetail GmbH',         'DE987654321',  'DE', 'Frankfurt',  '60311','Zeil 106',               'EuroRetail GmbH',         'HRB 98765', 'eingang@euroretail.de'),
('b0000000-0000-0000-0000-000000000004', 'MegaCorp Ltd',            'GB987654321',  'GB', 'Manchester', 'M1 1',  '1 Piccadilly Gardens',  'MegaCorp Ltd',            '98765432',  'payables@megacorp.co.uk'),
('b0000000-0000-0000-0000-000000000005', 'Slovenija Invest doo',    'SI98765432',   'SI', 'Ljubljana',  '1000', 'Dunajska cesta 20',      'Slovenija Invest doo',    '98765432',  'racuni@si-invest.si')
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 4. Generate 1000 invoices, lines, and tax subtotals via PL/pgSQL
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    v_raw_file_id  UUID := '00000000-0000-0000-0000-000000000001';

    v_supplier_ids UUID[] := ARRAY[
        'a0000000-0000-0000-0000-000000000001'::uuid,
        'a0000000-0000-0000-0000-000000000002'::uuid,
        'a0000000-0000-0000-0000-000000000003'::uuid,
        'a0000000-0000-0000-0000-000000000004'::uuid,
        'a0000000-0000-0000-0000-000000000005'::uuid,
        'a0000000-0000-0000-0000-000000000006'::uuid,
        'a0000000-0000-0000-0000-000000000007'::uuid,
        'a0000000-0000-0000-0000-000000000008'::uuid,
        'a0000000-0000-0000-0000-000000000009'::uuid,
        'a0000000-0000-0000-0000-000000000010'::uuid,
        'a0000000-0000-0000-0000-000000000011'::uuid,
        'a0000000-0000-0000-0000-000000000012'::uuid,
        'a0000000-0000-0000-0000-000000000013'::uuid,
        'a0000000-0000-0000-0000-000000000014'::uuid,
        'a0000000-0000-0000-0000-000000000015'::uuid,
        'a0000000-0000-0000-0000-000000000016'::uuid,
        'a0000000-0000-0000-0000-000000000017'::uuid,
        'a0000000-0000-0000-0000-000000000018'::uuid,
        'a0000000-0000-0000-0000-000000000019'::uuid,
        'a0000000-0000-0000-0000-000000000020'::uuid
    ];

    v_customer_ids UUID[] := ARRAY[
        'b0000000-0000-0000-0000-000000000001'::uuid,
        'b0000000-0000-0000-0000-000000000002'::uuid,
        'b0000000-0000-0000-0000-000000000003'::uuid,
        'b0000000-0000-0000-0000-000000000004'::uuid,
        'b0000000-0000-0000-0000-000000000005'::uuid
    ];

    -- Weighted arrays (repeat entries to bias probability)
    v_currencies    TEXT[] := ARRAY['EUR','EUR','EUR','EUR','EUR','EUR','EUR','EUR','USD','GBP'];
    v_inv_types     TEXT[] := ARRAY['380','380','380','380','380','380','380','380','381','384'];
    v_peppol_states TEXT[] := ARRAY['RECEIVED','RECEIVED','RECEIVED','RECEIVED','TRANSIT','SENT','SENT','FAILED','DRAFT','DRAFT'];
    v_directions    TEXT[] := ARRAY['received','received','received','received','received','sent','sent','sent'];
    v_pay_means     TEXT[] := ARRAY['30','30','30','30','31','42','48','58'];
    -- Tax profiles: (category, percent)
    v_tax_cats      TEXT[]    := ARRAY['S','S','S','S','S','S','S','Z','E','AE'];
    v_tax_percents  NUMERIC[] := ARRAY[21,21,21,21,21,21,6,0,0,0];

    -- Line item descriptions
    v_descs TEXT[] := ARRAY[
        'Software licence fee', 'Consulting services', 'Hosting services', 'Support & maintenance',
        'Hardware supply', 'Training services', 'Data processing', 'Marketing services',
        'Design services', 'Cloud storage', 'API access fee', 'Professional services',
        'Project management', 'IT infrastructure', 'SaaS subscription', 'Integration services',
        'Analytics platform', 'Security audit', 'Content delivery', 'Platform fee'
    ];

    -- Loop variables
    i               INT;
    j               INT;
    v_inv_id        UUID;
    v_supplier_id   UUID;
    v_customer_id   UUID;
    v_currency      TEXT;
    v_inv_type      TEXT;
    v_direction     TEXT;
    v_peppol_state  TEXT;
    v_pay_means     TEXT;
    v_tax_cat       TEXT;
    v_tax_pct       NUMERIC;
    v_issue_date    DATE;
    v_due_date      DATE;
    v_delivery_date DATE;
    v_tax_excl      NUMERIC;
    v_tax_amt       NUMERIC;
    v_tax_incl      NUMERIC;
    v_payable       NUMERIC;
    v_line_ext      NUMERIC;
    v_line_count    INT;
    v_remaining     NUMERIC;
    v_line_amt      NUMERIC;
    v_qty           NUMERIC;
    v_unit_price    NUMERIC;
    v_rand_idx      INT;
    v_order_ref     TEXT;
    v_buyer_ref     TEXT;
    v_acct_cost     TEXT;
    v_invoice_num   TEXT;

BEGIN
    FOR i IN 1..1000 LOOP
        v_inv_id := gen_random_uuid();

        -- Pick random supplier and customer (ensure different parties)
        v_rand_idx    := 1 + floor(random() * 20)::int;
        v_supplier_id := v_supplier_ids[v_rand_idx];
        v_rand_idx    := 1 + floor(random() * 5)::int;
        v_customer_id := v_customer_ids[v_rand_idx];

        -- Pick random enums
        v_currency     := v_currencies   [1 + floor(random() * 10)::int];
        v_inv_type     := v_inv_types    [1 + floor(random() * 10)::int];
        v_direction    := v_directions   [1 + floor(random() * 8)::int];
        v_peppol_state := v_peppol_states[1 + floor(random() * 10)::int];
        v_pay_means    := v_pay_means    [1 + floor(random() * 8)::int];
        v_rand_idx     := 1 + floor(random() * 10)::int;
        v_tax_cat      := v_tax_cats    [v_rand_idx];
        v_tax_pct      := v_tax_percents[v_rand_idx];

        -- Dates: spread across 2023-2025
        v_issue_date    := DATE '2023-01-01' + floor(random() * 730)::int;
        v_due_date      := v_issue_date + (15 + floor(random() * 46)::int);  -- net 15-60
        v_delivery_date := v_issue_date + floor(random() * 10)::int;

        -- Amounts: net between 100 and 50000
        v_tax_excl := ROUND((100 + random() * 49900)::numeric, 2);
        v_tax_amt  := ROUND(v_tax_excl * v_tax_pct / 100, 2);
        v_tax_incl := v_tax_excl + v_tax_amt;
        v_payable  := v_tax_incl;   -- prepaid = 0
        v_line_ext := v_tax_excl;   -- document-level allowances/charges = 0

        -- Optional references (70% have order ref, 50% have buyer ref)
        v_order_ref := CASE WHEN random() < 0.7 THEN 'PO-' || to_char(i, 'FM00000') || '-' || to_char(floor(random()*9000+1000)::int, 'FM0000') ELSE NULL END;
        v_buyer_ref := CASE WHEN random() < 0.5 THEN 'BUY-REF-' || to_char(i, 'FM00000') ELSE NULL END;
        v_acct_cost := CASE WHEN random() < 0.4 THEN 'CC-' || (floor(random()*9 + 1)::int)::text || to_char(floor(random()*999+100)::int,'FM000') ELSE NULL END;

        -- Invoice number
        v_invoice_num := CASE v_inv_type
            WHEN '381' THEN 'CN-' || to_char(v_issue_date, 'YYYY') || '-' || to_char(i, 'FM00000')
            WHEN '384' THEN 'COR-' || to_char(v_issue_date, 'YYYY') || '-' || to_char(i, 'FM00000')
            ELSE 'INV-' || to_char(v_issue_date, 'YYYY') || '-' || to_char(i, 'FM00000')
        END;

        INSERT INTO invoices (
            id, raw_file_id, invoice_number, invoice_type, direction,
            issue_date, due_date, currency,
            supplier_id, customer_id,
            payable_amount, tax_amount, tax_exclusive_amount, tax_inclusive_amount,
            line_extension_amount,
            customization_id, profile_id,
            order_reference_id, buyer_reference, accounting_cost,
            delivery_actual_delivery_date,
            payment_means_code,
            peppol_state
        ) VALUES (
            v_inv_id, v_raw_file_id, v_invoice_num, v_inv_type, v_direction,
            v_issue_date, v_due_date, v_currency,
            v_supplier_id, v_customer_id,
            v_payable, v_tax_amt, v_tax_excl, v_tax_incl,
            v_line_ext,
            'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0',
            'urn:fdc:peppol.eu:2017:poacc:billing:01:1.0',
            v_order_ref, v_buyer_ref, v_acct_cost,
            v_delivery_date,
            v_pay_means,
            v_peppol_state
        );

        -- -----------------------------------------------------------------
        -- Invoice lines: 2-5 lines, amounts sum to v_tax_excl
        -- -----------------------------------------------------------------
        v_line_count := 2 + floor(random() * 4)::int;
        v_remaining  := v_tax_excl;

        FOR j IN 1..v_line_count LOOP
            IF j < v_line_count THEN
                -- Take a random slice between 10% and 60% of remaining
                v_line_amt := ROUND(v_remaining * (0.10 + random() * 0.50), 2);
            ELSE
                v_line_amt := ROUND(v_remaining, 2);
            END IF;
            v_remaining  := v_remaining - v_line_amt;

            v_qty        := (1 + floor(random() * 20))::numeric;
            v_unit_price := ROUND(v_line_amt / v_qty, 6);

            INSERT INTO invoice_lines (
                id, invoice_id, line_number, description,
                quantity, unit_price, line_amount,
                tax_category, tax_percent,
                item_name
            ) VALUES (
                gen_random_uuid(), v_inv_id, j::text,
                v_descs[1 + floor(random() * 20)::int],
                v_qty, v_unit_price, v_line_amt,
                v_tax_cat, v_tax_pct,
                v_descs[1 + floor(random() * 20)::int]
            );
        END LOOP;

        -- -----------------------------------------------------------------
        -- Tax subtotal: one per invoice (matches header tax amounts)
        -- -----------------------------------------------------------------
        INSERT INTO tax_subtotals (
            id, invoice_id,
            tax_category, tax_percent,
            taxable_amount, tax_amount
        ) VALUES (
            gen_random_uuid(), v_inv_id,
            v_tax_cat, v_tax_pct,
            v_tax_excl, v_tax_amt
        );

    END LOOP;

    RAISE NOTICE 'Seed complete: 1000 invoices inserted.';
END;
$$;

COMMIT;
