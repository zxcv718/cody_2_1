# Python 콘솔 가계부

파일 입출력 기반의 콘솔 가계부 애플리케이션입니다. 표준 라이브러리만 사용하며, 데이터는 JSONL 파일로 영구 저장됩니다.

## 실행 방법

```bash
python -m budget_app <command> [options]
```

모든 명령은 `--help`를 지원합니다.

```bash
python -m budget_app --help
python -m budget_app add --help
python -m budget_app summary --help
```

저장 폴더는 기본적으로 `./data`이며, `--data-dir`로 변경할 수 있습니다.

```bash
python -m budget_app --data-dir ./my-data list
python -m budget_app list --data-dir ./my-data
```

## 저장 파일 위치와 형식

기본 저장 폴더 `./data`에 아래 3개 파일이 자동 생성됩니다.

| 파일 | 형식 | 설명 |
| --- | --- | --- |
| `transactions.jsonl` | JSONL | 거래 내역 |
| `categories.jsonl` | JSONL | 카테고리 목록 |
| `budgets.jsonl` | JSONL | 월별 예산 |

초기 실행 시 카테고리 파일이 비어 있으면 기본 카테고리가 자동 생성됩니다.

```text
food, transport, rent, salary, etc
```

## 주요 명령 예시

### 거래 추가

`add`는 대화형 입력으로 동작합니다. 날짜, 타입, 카테고리, 금액을 잘못 입력하면 오류와 힌트를 출력하고 같은 항목을 다시 입력받습니다.

```bash
python -m budget_app add
```

입력 예시:

```text
날짜(YYYY-MM-DD): 2024-01-15
타입(income/expense): expense
카테고리: food
금액(양수): 15000
메모(선택): 점심
태그(쉼표로 구분, 없으면 엔터): meal
[저장 완료] id=TX-000001
```

### 거래 목록

```bash
python -m budget_app list --limit 10
```

### 거래 검색

```bash
python -m budget_app search --from 2024-01-01 --to 2024-01-31
python -m budget_app search --category food --type expense
python -m budget_app search --q 점심
python -m budget_app search --tag meal
```

### 월별 요약

```bash
python -m budget_app summary --month 2024-01 --top 3
```

### 예산 설정/조회

```bash
python -m budget_app budget set --month 2024-01 --amount 500000
python -m budget_app budget show --month 2024-01
python -m budget_app budget list
```

예산이 설정된 월은 `summary`에서 사용률과 초과 경고를 함께 출력합니다.

### 카테고리 관리

```bash
python -m budget_app category add
python -m budget_app category add --name culture
python -m budget_app category list
python -m budget_app category remove --name culture
```

사용 중인 카테고리는 삭제할 수 없습니다. 먼저 해당 거래의 카테고리를 수정해야 합니다.

### 거래 수정

이 앱의 `update`는 옵션 기반 방식으로 고정합니다.

```bash
python -m budget_app update --id TX-000001 --amount 18000
python -m budget_app update --id TX-000001 --date 2024-01-16 --memo "저녁"
python -m budget_app update --id TX-000001 --tags meal,dinner
```

### 거래 삭제

```bash
python -m budget_app delete --id TX-000001
```

### CSV 내보내기

`export`는 `--month YYYY-MM` 또는 `--from YYYY-MM-DD --to YYYY-MM-DD` 중 하나 이상의 기간 조건이 필요합니다.

```bash
python -m budget_app export --out export.csv --month 2024-01
python -m budget_app export --out export.csv --from 2024-01-01 --to 2024-01-31
```

### CSV 가져오기

```bash
python -m budget_app import --from import.csv
```

유효하지 않은 행은 건너뛰고, 처리 결과를 `imported`, `skipped`로 출력합니다.

## Import/Export CSV 스키마

CSV는 UTF-8 인코딩과 헤더를 사용합니다.

| column | required | 설명 |
| --- | --- | --- |
| `date` | Y | `YYYY-MM-DD` |
| `type` | Y | `income` / `expense` |
| `category` | Y | 등록된 카테고리 |
| `amount` | Y | 양수 정수 |
| `memo` | N | 문자열 |
| `tags` | N | 쉼표(`,`) 구분 문자열 |

예시:

```csv
date,type,category,amount,memo,tags
2024-01-15,expense,food,15000,점심,meal
2024-01-14,income,salary,3000000,월급,
```

## 구현 구조

| 모듈 | 책임 |
| --- | --- |
| `budget_app.models` | `dataclass` 기반 데이터 구조 |
| `budget_app.storage` | JSONL 파일 I/O, 제너레이터 스트리밍, 원자적 재작성 |
| `budget_app.services` | 거래/예산/카테고리 비즈니스 로직 |
| `budget_app.command_validation` | 명령 입력값 검증과 대화형 재입력 기준 |
| `budget_app.cli` | `argparse` 기반 CLI |
| `budget_app.decorators` | 공통 예외 처리 데코레이터 |
| `budget_app.validators` | 날짜, 월, 금액, 타입, 태그 검증 |

거래 파일 조회는 `TransactionRepository.iter_transactions()` 제너레이터를 통해 한 줄씩 스트리밍합니다. `list`는 제한 개수만 유지하고, `summary`와 `export`는 파일을 순회하며 필요한 결과만 집계/출력합니다.

오류는 스택트레이스 대신 원인과 해결 힌트로 출력하며, 오류 종료 시 0이 아닌 exit code를 반환합니다.
