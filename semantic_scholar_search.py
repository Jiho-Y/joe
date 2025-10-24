import requests
import pandas as pd
import openpyxl
import time
from pathlib import Path
from datetime import datetime
import sys
import os

# Semantic Scholar API v1 엔드포인트
API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

# (선택사항) Semantic Scholar API 키
API_KEY = ""  # 여기에 API 키를 입력하세요


def print_header(title):
    """섹션 헤더 출력"""
    width = 80
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def print_error_box(title, message, suggestions=None):
    """오류를 가시화하여 박스 형태로 출력"""
    width = 70
    print("\n" + "═" * width)
    print(f"╔{'═' * (width - 2)}╗")
    print(f"║ ❌ {title.center(width - 6)} ║")
    print(f"╠{'═' * (width - 2)}╣")

    for line in message.split('\n'):
        if line.strip():
            words = line.split()
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 <= width - 6:
                    current_line += word + " "
                else:
                    print(f"║ {current_line.ljust(width - 4)} ║")
                    current_line = word + " "
            if current_line:
                print(f"║ {current_line.ljust(width - 4)} ║")

    if suggestions:
        print(f"╠{'═' * (width - 2)}╣")
        print(f"║ 💡 {'해결 방법:'.ljust(width - 6)} ║")
        for i, suggestion in enumerate(suggestions, 1):
            lines = suggestion.split('\n')
            for j, line in enumerate(lines):
                prefix = f"  {i}. " if j == 0 else "     "
                print(f"║ {prefix}{line.ljust(width - 6 - len(prefix))} ║")

    print(f"╚{'═' * (width - 2)}╝")
    print("═" * width + "\n")


def print_progress(current, total, status=""):
    """진행 상황을 시각적으로 표시"""
    bar_length = 40
    filled = int(bar_length * current / total)
    bar = '█' * filled + '░' * (bar_length - filled)
    percent = 100 * current / total
    print(f"\r진행: [{bar}] {percent:.1f}% {status}", end='', flush=True)


def exponential_backoff_wait(attempt, base_wait=1, max_wait=1048):
    """
    지수 백오프 대기 시간 계산 및 시각화

    Args:
        attempt: 현재 시도 횟수 (0부터 시작)
        base_wait: 기본 대기 시간 (초)
        max_wait: 최대 대기 시간 (초) - 기본 1048초(약 17.5분)
    """
    wait_time = min(base_wait * (2 ** attempt), max_wait)

    print(f"\n⏳ 재시도 대기 중... ({wait_time}초 = {wait_time/60:.1f}분)")
    print("   대기 진행: ", end='', flush=True)

    # 10초마다 점 하나씩 출력
    dots_to_show = int(wait_time / 10)
    for i in range(dots_to_show):
        time.sleep(10)
        print("●", end='', flush=True)

    # 나머지 시간 대기
    remaining = wait_time - (dots_to_show * 10)
    if remaining > 0:
        time.sleep(remaining)
        print("●", end='', flush=True)

    print(" 완료!\n")
    return wait_time


def search_semantic_scholar_single(keyword, limit=100, offset=0, max_retries=10):
    """
    Semantic Scholar에서 단일 요청으로 논문 검색

    Args:
        keyword: 검색 키워드
        limit: 한 번에 가져올 결과 수 (최대 100)
        offset: 시작 위치
        max_retries: 재시도 최대 횟수 (10회로 증가)

    Returns:
        dict: {'data': 논문 리스트, 'total': 전체 결과 수} 또는 None
    """
    params = {
        'query': keyword,
        'limit': min(limit, 100),
        'offset': offset,
        'fields': 'title,authors,year,abstract,url,venue,citationCount,publicationDate,paperId,externalIds'
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Academic Research Tool)'
    }

    if API_KEY:
        headers['x-api-key'] = API_KEY

    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"📌 재시도 {attempt + 1}/{max_retries} (offset={offset})")

            response = requests.get(API_URL, params=params, headers=headers, timeout=300)

            # Rate limit 처리 (429 에러)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))

                print_error_box(
                    "Rate Limit 초과",
                    f"API 요청 한도를 초과했습니다.\n"
                    f"서버가 {retry_after}초 후 재시도를 권장합니다.\n"
                    f"현재 시도: {attempt + 1}/{max_retries}",
                    [
                        "지수 백오프를 사용하여 대기 후 재시도합니다.",
                        "프로그램을 중단하지 않고 계속 진행합니다."
                    ]
                )

                if attempt < max_retries - 1:
                    # 서버 권장 시간과 지수 백오프 중 큰 값 사용
                    exponential_wait = 2 ** attempt
                    wait_time = max(retry_after, exponential_wait)
                    exponential_backoff_wait(0, base_wait=wait_time, max_wait=1048)
                    continue
                else:
                    print("❌ 최대 재시도 횟수를 초과했습니다.")
                    return None

            # HTTP 오류 체크
            response.raise_for_status()

            results = response.json()

            if 'data' not in results:
                print_error_box(
                    "API 응답 형식 오류",
                    f"예상치 못한 API 응답 형식입니다.",
                    ["잠시 후 재시도합니다."]
                )
                if attempt < max_retries - 1:
                    exponential_backoff_wait(attempt, base_wait=2, max_wait=1048)
                    continue
                return None

            return results

        except requests.exceptions.Timeout:
            print_error_box(
                "타임아웃 오류 (5분)",
                f"서버 응답 시간 초과\n시도: {attempt + 1}/{max_retries}",
                ["네트워크가 불안정할 수 있습니다.", "재시도합니다."]
            )

            if attempt < max_retries - 1:
                exponential_backoff_wait(attempt, base_wait=5, max_wait=1048)
            else:
                return None

        except requests.exceptions.HTTPError as http_err:
            status_code = response.status_code

            if status_code >= 500:
                print_error_box(
                    f"서버 오류 ({status_code})",
                    f"Semantic Scholar 서버에 문제가 발생했습니다.\n시도: {attempt + 1}/{max_retries}",
                    ["서버가 일시적으로 불안정할 수 있습니다.", "재시도합니다."]
                )

                if attempt < max_retries - 1:
                    exponential_backoff_wait(attempt, base_wait=10, max_wait=1048)
                else:
                    return None
            else:
                print_error_box(
                    f"HTTP 오류 ({status_code})",
                    str(http_err),
                    ["재시도합니다."]
                )
                if attempt < max_retries - 1:
                    exponential_backoff_wait(attempt, base_wait=5, max_wait=1048)
                else:
                    return None

        except requests.exceptions.RequestException as req_err:
            print_error_box(
                "네트워크 오류",
                f"요청 처리 중 오류 발생\n오류: {str(req_err)}",
                ["네트워크 연결을 확인하고 재시도합니다."]
            )
            if attempt < max_retries - 1:
                exponential_backoff_wait(attempt, base_wait=3, max_wait=1048)
            else:
                return None

        except Exception as e:
            print_error_box(
                "알 수 없는 오류",
                f"예상치 못한 오류 발생\n오류: {str(e)}",
                ["재시도합니다."]
            )
            if attempt < max_retries - 1:
                exponential_backoff_wait(attempt, base_wait=5, max_wait=1048)
            else:
                return None

    return None


def search_with_pagination(keyword, max_results=1000):
    """
    Pagination을 사용하여 100개 이상의 논문 검색

    Args:
        keyword: 검색 키워드
        max_results: 최대 검색 결과 수

    Returns:
        list: 논문 데이터 리스트
    """
    all_papers = []
    offset = 0
    batch_size = 100

    print(f"\n🔍 '{keyword}' 검색 시작...")

    # 첫 번째 요청으로 전체 결과 수 확인
    first_result = search_semantic_scholar_single(keyword, limit=batch_size, offset=0)

    if first_result is None:
        print(f"❌ '{keyword}' 검색 실패")
        return []

    total_available = first_result.get('total', 0)
    papers = first_result.get('data', [])

    if not papers:
        print(f"⚠️  '{keyword}' 검색 결과 없음")
        return []

    all_papers.extend(papers)
    print(f"   ✓ 배치 1: {len(papers)}개 수집 (전체 약 {total_available}개 존재)")

    # 100개 미만이면 종료
    if len(papers) < batch_size:
        print(f"   ✓ 검색 완료: 총 {len(all_papers)}개")
        return all_papers

    # 100개 이상이면 pagination 계속
    target = min(max_results, total_available)
    batch_num = 2

    while len(all_papers) < target:
        offset += batch_size
        remaining = target - len(all_papers)
        current_limit = min(batch_size, remaining)

        # API 키 없으면 Rate Limit 준수 (1초 대기)
        if not API_KEY:
            print(f"   ⏳ Rate Limit 준수를 위해 1.2초 대기...")
            time.sleep(1.2)

        print(f"   📥 배치 {batch_num}: offset={offset}, limit={current_limit}")

        result = search_semantic_scholar_single(keyword, limit=current_limit, offset=offset)

        if result is None:
            print(f"   ⚠️  배치 {batch_num} 검색 실패 (계속 진행)")
            break

        papers = result.get('data', [])

        if not papers:
            print(f"   ✓ 더 이상 결과 없음")
            break

        all_papers.extend(papers)
        print(f"   ✓ 배치 {batch_num}: {len(papers)}개 수집 (누적: {len(all_papers)}개)")

        batch_num += 1

        # 전체 결과를 모두 가져왔으면 종료
        if len(all_papers) >= total_available:
            print(f"   ✓ 전체 결과 수집 완료")
            break

    print(f"✅ '{keyword}' 검색 완료: 총 {len(all_papers)}개 수집\n")
    return all_papers


def format_chicago_citation(paper_data):
    """Chicago 스타일 인용 형식 생성"""
    # 저자 처리
    authors_list = paper_data.get('authors', [])
    if authors_list:
        if len(authors_list) == 1:
            authors_str = authors_list[0].get('name', 'Unknown')
        elif len(authors_list) == 2:
            authors_str = f"{authors_list[0].get('name', 'Unknown')} and {authors_list[1].get('name', 'Unknown')}"
        elif len(authors_list) > 2:
            authors_str = f"{authors_list[0].get('name', 'Unknown')} et al."
        else:
            authors_str = "Unknown Author"
    else:
        authors_str = "Unknown Author"

    # 연도
    year = paper_data.get('year', 'n.d.')

    # 제목
    title = paper_data.get('title', 'No title')

    # Venue
    venue = paper_data.get('venue', 'Unknown venue')

    # Citation Count
    citation_count = paper_data.get('citationCount', 0)

    # Chicago 형식: Author(s). Year. "Title." Venue. (Cited by: count)
    if venue and venue != 'Unknown venue':
        citation = f'{authors_str}. {year}. "{title}." {venue}. (Cited by: {citation_count})'
    else:
        citation = f'{authors_str}. {year}. "{title}." (Cited by: {citation_count})'

    return citation


def process_papers(papers_data, keyword_label=""):
    """
    API에서 받은 논문 데이터를 엑셀에 저장하기 좋은 형태로 가공
    """
    if not papers_data:
        return []

    processed_list = []
    total = len(papers_data)

    print(f"📊 '{keyword_label}' 데이터 가공 중...")

    for idx, paper in enumerate(papers_data, 1):
        if idx % 20 == 0 or idx == total:
            print_progress(idx, total, f"({idx}/{total})")

        # 저자 리스트를 문자열로 변환
        authors_list = paper.get('authors', [])
        if authors_list:
            authors = ", ".join([author.get('name', 'Unknown') for author in authors_list])
        else:
            authors = "No authors listed"

        # Abstract 길이 체크
        abstract = paper.get('abstract', 'No abstract available')
        if abstract and len(abstract) > 32767:
            abstract = abstract[:32760] + "..."

        # DOI 추출
        doi = 'N/A'
        external_ids = paper.get('externalIds', {})
        if external_ids:
            doi = external_ids.get('DOI', 'N/A')

        # Chicago 인용 형식 생성
        chicago_citation = format_chicago_citation(paper)

        processed_list.append({
            'Keyword': keyword_label,  # 어떤 키워드로 검색되었는지 표시
            'Paper ID': paper.get('paperId', 'N/A'),
            'DOI': doi,
            'Title': paper.get('title', 'No title'),
            'Authors': authors,
            'Year': paper.get('year', 'N/A'),
            'Publication Date': paper.get('publicationDate', 'N/A'),
            'Venue': paper.get('venue', 'N/A'),
            'Citation Count': paper.get('citationCount', 0),
            'Abstract': abstract,
            'URL': paper.get('url', 'N/A'),
            'Chicago Citation': chicago_citation,
        })

    print()
    print(f"✅ {len(processed_list)}개 데이터 가공 완료\n")

    return processed_list


def load_existing_excel(filepath):
    """
    기존 엑셀 파일 불러오기

    Args:
        filepath: 엑셀 파일 경로

    Returns:
        list: 논문 데이터 리스트 또는 빈 리스트
    """
    if not os.path.exists(filepath):
        print(f"⚠️  파일을 찾을 수 없습니다: {filepath}")
        return []

    try:
        print(f"\n📂 기존 파일 불러오는 중: {filepath}")
        df = pd.read_excel(filepath, sheet_name='Papers')

        # DataFrame을 dictionary 리스트로 변환
        existing_papers = df.to_dict('records')

        print(f"✅ 기존 논문 {len(existing_papers)}개 불러오기 완료")

        # 통계 출력
        if existing_papers:
            keywords_count = {}
            for paper in existing_papers:
                kw = paper.get('Keyword', 'Unknown')
                keywords_count[kw] = keywords_count.get(kw, 0) + 1

            print(f"\n📊 기존 데이터 통계:")
            for kw, count in keywords_count.items():
                print(f"   - '{kw}': {count}개")

        return existing_papers

    except Exception as e:
        print_error_box(
            "파일 불러오기 오류",
            f"엑셀 파일을 불러오는 중 오류 발생\n오류: {str(e)}",
            ["파일이 손상되었거나 형식이 올바르지 않을 수 있습니다."]
        )
        return []


def remove_duplicates_by_doi(all_papers_list):
    """
    DOI를 기준으로 중복 제거 및 키워드별 통계 생성
    - DOI가 있는 논문: DOI로 중복 제거
    - DOI가 없는 논문 (N/A): Paper ID로 중복 제거

    Returns:
        tuple: (unique_papers, keyword_duplicates)
               unique_papers: 중복 제거된 논문 리스트
               keyword_duplicates: 키워드별 중복 개수 딕셔너리
    """
    print_header("중복 제거 처리")

    original_count = len(all_papers_list)
    print(f"원본 논문 수: {original_count}개")

    # DOI가 있는 논문과 없는 논문 분리
    papers_with_doi = {}
    papers_without_doi = {}

    # 키워드별 중복 카운트 초기화
    keyword_duplicates = {}

    for paper in all_papers_list:
        doi = paper.get('DOI', 'N/A')
        paper_id = paper.get('Paper ID', 'N/A')
        keyword = paper.get('Keyword', 'Unknown')

        is_duplicate = False

        if doi != 'N/A':
            # DOI가 있으면 DOI를 키로 사용 (먼저 발견된 것 유지)
            if doi not in papers_with_doi:
                papers_with_doi[doi] = paper
            else:
                is_duplicate = True
        else:
            # DOI가 없으면 Paper ID를 키로 사용
            if paper_id != 'N/A' and paper_id not in papers_without_doi:
                papers_without_doi[paper_id] = paper
            else:
                is_duplicate = True

        # 중복이면 키워드별 카운트 증가
        if is_duplicate:
            keyword_duplicates[keyword] = keyword_duplicates.get(keyword, 0) + 1

    # 합치기
    unique_papers = list(papers_with_doi.values()) + list(papers_without_doi.values())

    removed_count = original_count - len(unique_papers)

    print(f"DOI 기준 고유 논문: {len(papers_with_doi)}개")
    print(f"DOI 없는 논문 (Paper ID 기준): {len(papers_without_doi)}개")
    print(f"제거된 중복 논문: {removed_count}개")
    print(f"최종 고유 논문 수: {len(unique_papers)}개")

    # 키워드별 중복 통계 출력
    if keyword_duplicates:
        print(f"\n📊 키워드별 중복 제거 내역:")
        for keyword, count in keyword_duplicates.items():
            print(f"   • '{keyword}': {count}개 중복 제거")

    if removed_count > 0:
        print(f"\n✅ 총 {removed_count}개의 중복 논문이 제거되었습니다.")
    else:
        print(f"\n✅ 중복 논문이 없습니다.")

    return unique_papers, keyword_duplicates


def save_to_excel(papers_list, filename="papers.xlsx"):
    """
    가공된 논문 리스트를 엑셀 파일로 저장
    """
    if not papers_list:
        print("⚠️  저장할 논문 데이터가 없습니다.")
        return False

    try:
        print(f"\n💾 엑셀 파일 생성 중: {filename}")

        df = pd.DataFrame(papers_list)

        # 파일 경로를 절대 경로로 변환
        output_path = Path(filename).absolute()

        # 엑셀 파일로 저장
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Papers')

            # 워크시트 가져오기
            worksheet = writer.sheets['Papers']

            # 열 너비 자동 조정
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter

                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass

                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        print(f"\n{'=' * 70}")
        print(f"✅ 성공! 파일이 저장되었습니다.")
        print(f"{'=' * 70}")
        print(f"📁 파일 경로: {output_path}")
        print(f"📊 논문 수: {len(papers_list)}개")
        print(f"📅 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 70}\n")

        return True

    except PermissionError:
        print_error_box(
            "파일 권한 오류",
            f"'{filename}' 파일에 대한 쓰기 권한이 없습니다.",
            [
                "파일이 Excel에서 열려있는지 확인하세요.",
                "파일을 닫고 다시 시도하세요."
            ]
        )
        return False

    except Exception as e:
        print_error_box(
            "파일 저장 오류",
            f"엑셀 파일 저장 중 오류 발생\n오류: {str(e)}",
            ["충분한 디스크 공간이 있는지 확인하세요."]
        )
        return False


def get_keyword_sets():
    """
    사용자로부터 유연한 개수의 키워드 입력받기
    """
    print_header("키워드 입력")
    print("📝 검색 키워드를 입력해주세요.")
    print("   (각 키워드는 여러 단어를 포함할 수 있습니다)")
    print("   예: waam hastelloy, inconel 718, additive manufacturing\n")

    # 키워드 개수 선택
    while True:
        print("키워드 입력 방식을 선택하세요:")
        print("  1. 키워드 개수 지정")
        print("  2. 하나씩 입력 (계속 추가 여부 선택)")

        choice = input("\n선택 (1 또는 2): ").strip()

        if choice == '1':
            while True:
                try:
                    num_keywords = int(input("입력할 키워드 개수: ").strip())
                    if num_keywords > 0:
                        break
                    else:
                        print("⚠️  1 이상의 숫자를 입력해주세요.")
                except ValueError:
                    print("⚠️  올바른 숫자를 입력해주세요.")

            keywords = []
            for i in range(num_keywords):
                while True:
                    keyword = input(f"키워드 {i+1}: ").strip()
                    if keyword:
                        keywords.append(keyword)
                        break
                    else:
                        print("⚠️  키워드를 입력해주세요.")
            break

        elif choice == '2':
            keywords = []
            keyword_num = 1

            while True:
                keyword = input(f"키워드 {keyword_num}: ").strip()
                if keyword:
                    keywords.append(keyword)
                    keyword_num += 1

                    more = input("키워드를 더 추가하시겠습니까? (y/n): ").strip().lower()
                    if more != 'y':
                        break
                else:
                    print("⚠️  키워드를 입력해주세요.")

            if keywords:
                break
        else:
            print("⚠️  1 또는 2를 선택해주세요.\n")

    print(f"\n입력된 키워드 ({len(keywords)}개):")
    for i, kw in enumerate(keywords, 1):
        print(f"  {i}. {kw}")

    confirm = input("\n이대로 진행하시겠습니까? (y/n): ").strip().lower()
    if confirm != 'y':
        print("프로그램을 종료합니다.")
        sys.exit(0)

    return keywords


def choose_mode():
    """
    작업 모드 선택: 새로 만들기 vs 기존 파일에 추가

    Returns:
        tuple: (mode, existing_file_path)
               mode: 'new' 또는 'append'
               existing_file_path: 기존 파일 경로 (mode='append'일 때만)
    """
    print_header("작업 모드 선택")
    print("원하는 작업을 선택하세요:")
    print("  1. 새로운 검색 (새 파일 생성)")
    print("  2. 기존 파일에 추가 (중복 제거)")

    while True:
        choice = input("\n선택 (1 또는 2): ").strip()

        if choice == '1':
            return 'new', None

        elif choice == '2':
            filepath = input("기존 엑셀 파일 경로를 입력하세요: ").strip()

            # 따옴표 제거
            filepath = filepath.strip('"').strip("'")

            if os.path.exists(filepath):
                return 'append', filepath
            else:
                print(f"⚠️  파일을 찾을 수 없습니다: {filepath}")
                retry = input("다시 입력하시겠습니까? (y/n): ").strip().lower()
                if retry != 'y':
                    print("새로운 검색 모드로 전환합니다.")
                    return 'new', None
        else:
            print("⚠️  1 또는 2를 선택해주세요.")


# --- 메인 실행 부분 ---
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("  🔬 Semantic Scholar 논문 검색 도구 v3.1 (macOS)")
    print("  📌 유연한 키워드 / 기존 파일 추가 / Chicago 인용 / 키워드별 중복 통계")
    print("=" * 80)

    if not API_KEY:
        print("\n⚠️  API 키가 설정되지 않았습니다.")
        print("   키 없이 사용 시 각 요청 사이 1.2초 대기합니다.")
        print("   대량 검색 시 시간이 오래 걸릴 수 있습니다.\n")
    else:
        print("\n✅ API 키가 설정되어 있습니다.\n")

    try:
        # 0. 작업 모드 선택
        mode, existing_file = choose_mode()

        # 기존 파일 불러오기 (append 모드일 경우)
        existing_papers = []
        if mode == 'append':
            existing_papers = load_existing_excel(existing_file)
            if not existing_papers:
                print("\n⚠️  기존 파일을 불러올 수 없습니다. 새로운 파일로 생성합니다.")
                mode = 'new'

        # 1. 키워드 입력
        keywords = get_keyword_sets()

        # 2. 각 키워드별로 검색 진행
        print_header("논문 검색 시작")
        all_papers_processed = []

        for i, keyword in enumerate(keywords, 1):
            print(f"\n{'─' * 80}")
            print(f"🔍 키워드 {i}/{len(keywords)}: '{keyword}'")
            print(f"{'─' * 80}")

            # Pagination으로 최대 1000개까지 검색
            papers_raw = search_with_pagination(keyword, max_results=1000)

            if papers_raw:
                # 데이터 가공
                papers_processed = process_papers(papers_raw, keyword_label=keyword)
                all_papers_processed.extend(papers_processed)
                print(f"✅ 키워드 {i} 완료: {len(papers_processed)}개 논문 수집\n")
            else:
                print(f"⚠️  키워드 {i} 검색 결과 없음\n")

        # 3. 전체 수집 결과 요약
        print_header("검색 결과 요약")
        print(f"새로 수집된 논문 수: {len(all_papers_processed)}개")

        for i, keyword in enumerate(keywords, 1):
            count = sum(1 for p in all_papers_processed if p['Keyword'] == keyword)
            print(f"  키워드 {i} ('{keyword}'): {count}개")

        if not all_papers_processed and not existing_papers:
            print("\n⚠️  검색된 논문이 없습니다. 프로그램을 종료합니다.")
            sys.exit(0)

        # 4. 기존 데이터와 합치기 (append 모드일 경우)
        if mode == 'append' and existing_papers:
            print(f"\n📂 기존 논문 데이터와 병합 중...")
            all_papers_combined = existing_papers + all_papers_processed
            print(f"   기존 논문: {len(existing_papers)}개")
            print(f"   새 논문: {len(all_papers_processed)}개")
            print(f"   병합 전 총합: {len(all_papers_combined)}개")
        else:
            all_papers_combined = all_papers_processed

        # 5. DOI 기준 중복 제거
        unique_papers, keyword_duplicates = remove_duplicates_by_doi(all_papers_combined)

        # 6. 엑셀 파일로 저장
        print_header("엑셀 파일 저장")

        if mode == 'append' and existing_file:
            # 기존 파일 덮어쓰기
            filename = existing_file
            print(f"💾 기존 파일을 업데이트합니다: {filename}")
        else:
            # 새 파일 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"semantic_scholar_results_{timestamp}.xlsx"

        success = save_to_excel(unique_papers, filename)

        if success:
            print("\n" + "=" * 80)
            print("🎉 프로그램을 성공적으로 완료했습니다!")
            print("=" * 80)
            print(f"📊 최종 통계:")
            print(f"   - 작업 모드: {'기존 파일 업데이트' if mode == 'append' else '새 파일 생성'}")
            if mode == 'append':
                print(f"   - 기존 논문 수: {len(existing_papers)}개")
                print(f"   - 새로 추가된 논문: {len(all_papers_processed)}개")
                print(f"   - 제거된 중복: {len(all_papers_combined) - len(unique_papers)}개")
            print(f"   - 검색 키워드: {len(keywords)}개")
            print(f"   - 최종 논문 수: {len(unique_papers)}개")
            print("=" * 80)
        else:
            print("\n⚠️  파일 저장 중 문제가 발생했습니다.")

    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 프로그램이 중단되었습니다.")
        sys.exit(0)

    except Exception as e:
        print_error_box(
            "예기치 않은 오류",
            f"프로그램 실행 중 예상치 못한 오류가 발생했습니다.\n오류: {str(e)}",
            ["프로그램을 다시 실행해보세요."]
        )
        sys.exit(1)
