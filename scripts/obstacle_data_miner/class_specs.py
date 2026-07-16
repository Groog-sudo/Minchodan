"""Collection policy for the exact 29-class obstacle taxonomy.

The goal of this file is to make data collection class-aware.  Each class has
positive search queries, exclusion notes, and near-miss classes that should be
collected as hard negatives or reviewed carefully.
"""

from __future__ import annotations

from dataclasses import dataclass

from config import TARGET_CLASSES


@dataclass(frozen=True)
class ClassSpec:
    class_id: int
    name: str
    include: str
    exclude: str
    search_queries: tuple[str, ...]
    hard_negatives: tuple[str, ...] = ()


CLASS_SPECS: dict[str, ClassSpec] = {
    "bicycle": ClassSpec(
        2,
        "bicycle",
        "Pedal bicycles, parked bicycles, bicycle wheels/frames visible enough for a box.",
        "Motorcycles and electric scooters.",
        ("bicycle sidewalk obstacle", "parked bicycle sidewalk", "자전거 인도 주차"),
        ("motorcycle", "scooter", "stroller"),
    ),
    "bus": ClassSpec(
        4,
        "bus",
        "Public buses, shuttle buses, large passenger buses.",
        "Trucks, vans, cars.",
        ("city bus street object detection", "bus road scene", "버스 도로 장면"),
        ("truck", "car"),
    ),
    "car": ClassSpec(
        5,
        "car",
        "Passenger cars, parked cars, taxis, compact SUVs if the local dataset treats them as cars.",
        "Buses, trucks, motorcycles.",
        ("parked car sidewalk edge", "car street object detection", "불법주정차 차량 인도"),
        ("bus", "truck", "motorcycle"),
    ),
    "carrier": ClassSpec(
        6,
        "carrier",
        "Hand carts, luggage carts, delivery carts, dollies, small wheeled carriers.",
        "Baby strollers, wheelchairs, tables/chairs.",
        ("hand cart sidewalk", "delivery cart sidewalk", "카트 인도 장애물", "손수레 보행로"),
        ("stroller", "wheelchair", "chair"),
    ),
    "cat": ClassSpec(
        7,
        "cat",
        "Cats in street or sidewalk scenes.",
        "Dogs, stuffed animals, statues.",
        ("cat sidewalk street", "cat road scene", "고양이 골목길"),
        ("dog",),
    ),
    "dog": ClassSpec(
        9,
        "dog",
        "Dogs in street or sidewalk scenes.",
        "Cats, plush toys, statues.",
        ("dog sidewalk street", "dog road scene", "강아지 산책 보행로"),
        ("cat",),
    ),
    "motorcycle": ClassSpec(
        12,
        "motorcycle",
        "Motorcycles, motorbikes, mopeds with motorcycle-like body.",
        "Bicycles, kickboards/e-scooters.",
        ("motorcycle parked sidewalk", "motorbike sidewalk obstacle", "오토바이 인도 주차"),
        ("bicycle", "scooter"),
    ),
    "movable_signage": ClassSpec(
        13,
        "movable_signage",
        "Portable sidewalk signs, A-frame signs, store standing signs, movable signboards.",
        "Fixed traffic signs, barricades, kiosks, posters on walls.",
        ("a-frame sign sidewalk", "sidewalk standing signboard", "입간판 보행로", "에이보드 간판"),
        ("traffic_sign", "barricade", "kiosk"),
    ),
    "person": ClassSpec(
        15,
        "person",
        "Pedestrians and people in road/sidewalk scenes.",
        "Mannequins, statues, posters with people.",
        ("pedestrian sidewalk object detection", "person street scene", "보행자 인도"),
        ("traffic_sign", "chair"),
    ),
    "scooter": ClassSpec(
        19,
        "scooter",
        "Kick scooters and electric scooters, especially parked on sidewalks.",
        "Motorcycles, bicycles, mobility wheelchairs.",
        ("electric scooter sidewalk parked", "kick scooter sidewalk", "전동 킥보드 인도 주차"),
        ("bicycle", "motorcycle", "wheelchair"),
    ),
    "stroller": ClassSpec(
        21,
        "stroller",
        "Baby strollers and prams.",
        "Wheelchairs, carts/carriers, chairs.",
        ("baby stroller sidewalk", "stroller street scene", "유모차 보행로"),
        ("wheelchair", "carrier", "chair"),
    ),
    "truck": ClassSpec(
        27,
        "truck",
        "Cargo trucks, delivery trucks, large utility trucks.",
        "Buses, vans/cars unless local labels include them as trucks.",
        ("delivery truck street", "truck road object detection", "화물차 도로 장면"),
        ("bus", "car"),
    ),
    "wheelchair": ClassSpec(
        28,
        "wheelchair",
        "Manual/electric wheelchairs and wheelchair users.",
        "Strollers, mobility scooters, chairs.",
        ("wheelchair sidewalk", "electric wheelchair sidewalk", "휠체어 보행로"),
        ("stroller", "scooter", "chair"),
    ),
    "barricade": ClassSpec(
        0,
        "barricade",
        "Roadwork barricades, folding safety barriers, temporary blocking barriers.",
        "Portable shop signs, traffic signs, cones if no barricade body is visible.",
        ("road barricade sidewalk", "construction barricade street", "공사 바리케이드 보행로"),
        ("movable_signage", "traffic_sign", "bollard"),
    ),
    "bench": ClassSpec(
        1,
        "bench",
        "Public benches and long outdoor seats.",
        "Single chairs, tables, railings.",
        ("sidewalk bench", "park bench street", "벤치 보행로"),
        ("chair", "table"),
    ),
    "bollard": ClassSpec(
        3,
        "bollard",
        "Short fixed posts used to block vehicle access on sidewalks/roads.",
        "Tall poles, tree trunks, traffic cones, sign posts.",
        ("bollard sidewalk", "short safety post sidewalk", "한국형 볼라드", "보도 볼라드"),
        ("pole", "tree_trunk", "traffic_sign"),
    ),
    "chair": ClassSpec(
        8,
        "chair",
        "Single chairs, outdoor cafe chairs, plastic chairs on sidewalks.",
        "Benches, wheelchairs, strollers.",
        ("chair sidewalk cafe", "outdoor chair street", "야외 의자 보행로"),
        ("bench", "wheelchair", "stroller"),
    ),
    "fire_hydrant": ClassSpec(
        10,
        "fire_hydrant",
        "Fire hydrants and fire plugs.",
        "Bollards, short posts, utility boxes.",
        ("fire hydrant sidewalk", "fire plug street", "소화전 보도"),
        ("bollard", "power_controller"),
    ),
    "kiosk": ClassSpec(
        11,
        "kiosk",
        "Outdoor kiosks, ticket/payment kiosks, information kiosks.",
        "Utility cabinets, vending machines unless the local class treats them as kiosks.",
        ("outdoor kiosk sidewalk", "ticket kiosk street", "야외 키오스크 보행로"),
        ("power_controller", "traffic_light_controller", "movable_signage"),
    ),
    "parking_meter": ClassSpec(
        14,
        "parking_meter",
        "Parking meters and parking payment posts.",
        "Traffic signal controllers, utility boxes, bollards.",
        ("parking meter street", "parking payment meter sidewalk", "주차 미터기"),
        ("bollard", "power_controller"),
    ),
    "pole": ClassSpec(
        16,
        "pole",
        "Tall slim poles: lamp posts, sign posts, utility poles.",
        "Bollards, tree trunks, sign plates.",
        ("street pole sidewalk", "lamp post sidewalk", "가로등 기둥 보행로", "표지판 기둥"),
        ("bollard", "tree_trunk", "traffic_sign"),
    ),
    "potted_plant": ClassSpec(
        17,
        "potted_plant",
        "Plants in pots or planters.",
        "Trees planted directly in the ground, bushes without visible pot.",
        ("potted plant sidewalk", "planter sidewalk obstacle", "화분 보행로"),
        ("tree_trunk", "bollard"),
    ),
    "power_controller": ClassSpec(
        18,
        "power_controller",
        "Electrical utility cabinets, distribution boxes, power control boxes.",
        "Traffic signal controller cabinets and kiosks.",
        (
            "utility cabinet sidewalk",
            "electrical control cabinet street",
            "분전함 보도",
            "전기 제어함 보행로",
        ),
        ("traffic_light_controller", "kiosk", "parking_meter"),
    ),
    "stop": ClassSpec(
        20,
        "stop",
        "Pedestrian stop signal or red stop-light target if the project keeps it separate.",
        "Generic traffic light heads if not specifically stop/red pedestrian signal.",
        ("pedestrian red stop light", "red pedestrian signal", "보행자 빨간불 신호등"),
        ("traffic_light", "traffic_sign"),
    ),
    "traffic_light": ClassSpec(
        23,
        "traffic_light",
        "Traffic signal heads/lamps for vehicles or pedestrians.",
        "Signal controller cabinets, poles without lamp heads.",
        ("traffic light street", "pedestrian traffic light", "신호등 본체"),
        ("traffic_light_controller", "pole", "traffic_sign"),
    ),
    "table": ClassSpec(
        22,
        "table",
        "Tables on sidewalks, outdoor cafe tables, folding tables.",
        "Chairs, benches, kiosks.",
        ("outdoor table sidewalk", "cafe table sidewalk", "야외 테이블 보행로"),
        ("chair", "bench", "kiosk"),
    ),
    "traffic_light_controller": ClassSpec(
        24,
        "traffic_light_controller",
        "Traffic signal controller cabinets/control boxes near intersections.",
        "Traffic light lamp heads, generic power cabinets, kiosks.",
        (
            "traffic signal controller cabinet",
            "traffic light control box sidewalk",
            "신호등 제어기",
            "교통신호 제어함",
        ),
        ("traffic_light", "power_controller", "kiosk"),
    ),
    "traffic_sign": ClassSpec(
        25,
        "traffic_sign",
        "Fixed road signs and sign plates.",
        "Portable shop signs, traffic lights, sign poles alone.",
        ("traffic sign street", "road sign sidewalk", "도로 표지판"),
        ("movable_signage", "traffic_light", "pole"),
    ),
    "tree_trunk": ClassSpec(
        26,
        "tree_trunk",
        "Visible tree trunks rooted in sidewalk/roadside areas.",
        "Poles, bollards, potted plants.",
        ("tree trunk sidewalk", "street tree trunk", "가로수 밑동 보도", "나무 밑동 보행로"),
        ("pole", "bollard", "potted_plant"),
    ),
}


def get_class_spec(class_id_or_name: str) -> ClassSpec:
    key = class_id_or_name.strip().lower()
    if key.isdigit():
        name = TARGET_CLASSES[int(key)]
        return CLASS_SPECS[name]
    key = key.replace("-", "_").replace(" ", "_")
    return CLASS_SPECS[key]


def validate_specs() -> None:
    expected_names = set(TARGET_CLASSES.values())
    spec_names = set(CLASS_SPECS)
    missing = expected_names - spec_names
    extra = spec_names - expected_names
    bad_ids = [
        f"{spec.name}:{spec.class_id}!={class_id}"
        for class_id, name in TARGET_CLASSES.items()
        for spec in [CLASS_SPECS[name]]
        if spec.class_id != class_id
    ]
    if missing or extra or bad_ids:
        raise ValueError(f"Invalid CLASS_SPECS missing={missing} extra={extra} bad_ids={bad_ids}")
