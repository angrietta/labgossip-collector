# LAB GOSSIP 수집기 (B안: AI 없음)

매일 아침(한국 시간 08:17) GitHub가 알아서 돌립니다. RSS 피드는 최근 수십 건만 담고 있어서(ScienceDaily 전체 피드는 약 5일치) 매일 모아 `data/pool.json`에 30일치를 쌓고, 보드는 그중 최근 8일치로 매일 다시 만듭니다. 보드는 주 단위(월요일 날짜)로 보관됩니다.

1. `feeds.txt`의 RSS를 모아 쌓습니다.
2. 여러 매체가 같은 소식을 냈으면 하나로 묶습니다. 지난주에 이미 본 소재는 "이미 본 소재"로 표시합니다.
3. 키워드 점수(`collector/rules.py`)로 상위 40개를 고릅니다. 형식 추천(CUT/PRESS/WEIGH/DOSE/SCALE), 주의 신호(동물 실험·상관관계 등)도 붙입니다.
4. 상위 40개는 원문 페이지에서 **숫자가 들어간 문장을 글자 그대로**, DOI와 함께 저장합니다.
5. 결과:
   - 보드: `https://<계정>.github.io/labgossip-collector/`
   - Claude가 읽는 요약: `https://<계정>.github.io/labgossip-collector/latest.md`
   - 원문 전체: `data/weeks/<날짜>.json`

최종 선별·대본·숫자 대조는 Claude 대화에서 합니다: "이번 주 보드 봐줘" + latest.md 주소.

## 고치기
- 피드 추가·끄기: `feeds.txt` (줄 앞 `#` = 끔)
- 점수 기준: `collector/rules.py`
- 지금 바로 실행: Actions 탭 → daily-collect → Run workflow
