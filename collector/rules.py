"""점수 규칙. AI 없이 키워드로만 1차로 거릅니다 — 최종 선별은 Claude 대화에서.
고치고 싶으면 여기 목록만 바꾸면 됩니다 (소문자, 단어 일부도 매칭)."""

# 실험 형식별 키워드: 가장 많이 맞는 형식을 '추천 형식'으로 표시
FORMATS = {
    "CUT":   ["inside", "organ", "gut", "heart", "liver", "plaque", "tumor", "skull", "fossil", "dissect",
              "anatomy", "bone", "egg", "seed", "cross-section", "brain shrink"],
    "PRESS": ["predict", "forecast", "doomsday", "by 2050", "by 2100", "years from now", "end of", "collapse",
              "population", "projection", "model shows", "will run out", "deadline"],
    "WEIGH": ["weight", "heavy", "load", "carry", "energy cost", "burden", "mass", "obesity", "backpack", "gravity"],
    "DOSE":  ["dose", "drug", "psilocybin", "caffeine", "alcohol", "nicotine", "cannabis", "supplement", "hormone",
              "antibiotic", "vaccine", "pill", "medication", "ozempic", "glp-1"],
    "SCALE": ["placebo", "diet", "food", "eat", "blueberr", "chocolate", "coffee", "vitamin", "fasting", "sugar",
              "versus", "compared with", "no difference", "no benefit", "trial", "omega", "fish oil", "red meat"],
}

# 가십 훅: "어?" 싶은 결과
HOOK = ["surpris", "unexpected", "contrary", "myth", "no effect", "did not", "didn't", "failed to", "fooled",
        "strange", "bizarre", "weird", "first time", "never before", "accidental", "mystery", "secret", "turns out",
        "backfire", "paradox", "wrong", "debunk", "overestimat", "underestimat", "actually", "shock"]

# 사람들이 클릭하는 생활 소재 (단어 앞부분 일치: "cat"은 cat/cats만, indicate는 안 걸림)
RELATABLE = ["sleep", "coffee", "dog", "cat", "chocolate", "cheese", "diet", "aging", "ageing", "alcohol", "phone",
             "social media", "exercise", "ozempic", "supplement", "baby", "babies", "love", "dating", "memory", "dementia", "alzheimer",
             "weight loss", "money", "music", "pets", "pet owner", "kids", "children", "teen", "brain", "stress", "happiness",
             "mouse", "mice", "fish", "bird", "monkey", "spider", "shark", "octopus", "dinosaur", "crayfish", "squid"]

# 영상으로 만들기 어려운 소재 / 홍보성 글
PENALTY_HARD = ["grant", "award", "funding", "appointed", "partnership", "conference", "webinar", "fellowship",
                "policy brief", "ranking", "named director", "announces", "celebrates", "launches"]
PENALTY_SOFT = ["quantum", "catalyst", "semiconductor", "photonic", "polymer", "electrolyte", "spintronic",
                "lattice", "algorithm", "superconduct", "nanomaterial", "perovskite", "tokamak"]

# THE CATCH 힌트: 한계가 될 만한 신호
CATCH_SIGNS = {
    "세포·시험관": ["in cells", "cell culture", "in vitro", "petri", "organoid", "lab-grown"],
    "상관관계": ["associated with", "linked to", "correlat", "tied to", "connected to"],
    "모델·시뮬레이션": ["simulation", "computer model", "modeling", "modelling", "projection"],
    "과장 의심 단어": ["breakthrough", "miracle", "cure", "game-changer", "revolutionary"],
}

# 동물만 나오고 사람 단어가 없으면 "동물 실험" 표시
ANIMALS = ["mice", "mouse", "rats", "rodent", "fish", "zebrafish", "monkey", "macaque", "chicks", "birds", "fowl",
           "fruit fl", "worms", "c. elegans", "pigs", "dogs", "bees", "ants"]
NOT_ANIMAL = ["fish oil", "fish-oil", "cod liver"]
HUMANS = ["people", "participants", "adults", "patients", "volunteers", "women", "men ", "children", "humans", "astronauts", "millions"]

MIN_SCORE = 1     # 이 점수 미만은 보드에 안 올림
SOURCE_CAP = 12   # 한 출처가 상위 40개를 다 차지하지 않게
TOP_N = 40
DAYS = 8          # 최근 며칠 치를 볼지
