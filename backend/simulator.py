mode = "normal"

INSTANCE = {
    "id":     "i-0a2f4c8e1b3d5a7f",
    "type":   "t3.medium",
    "region": "us-east-1",
    "label":  "t3.medium · us-east-1",
}

MODES = {
    "normal": {
        "cpu": (30, 65), "ram": (35, 60),
        # Red: logica por hora del dia en synthetic.py
        "label": "Normal",
    },
    "alta_carga": {
        "cpu": (70, 88), "ram": (65, 82),
        "net_in":  (4_000_000, 15_000_000),   # 4-15 MB/s - alta demanda de usuarios
        "net_out": (6_000_000, 25_000_000),   # 6-25 MB/s - sirviendo muchas respuestas
        "label": "Alta carga",
    },
    "critico": {
        "cpu": (88, 99), "ram": (82, 97),
        "net_in":  (10_000_000, 35_000_000),  # 10-35 MB/s - posible flood/saturacion
        "net_out": (1_000_000,   8_000_000),  # 1-8 MB/s  - servidor saturado, pocas respuestas
        "label": "Critico",
    },
    "nocturno": {
        "cpu": (8, 22), "ram": (18, 32),
        "net_in":  (20_000,   350_000),       # 20-350 KB/s - healthchecks, cron jobs
        "net_out": (8_000,    120_000),       # 8-120 KB/s
        "label": "Nocturno",
    },
}
