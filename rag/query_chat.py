import os
from chromadb import PersistentClient
from chromadb import Documents, EmbeddingFunction, Embeddings
import google.generativeai as genai  
import json
from datetime import datetime, date, timedelta
import re
from typing import Optional
import dotenv
dotenv.load_dotenv()
# ✅ 설정

CHROMA_DIR = "rag/chroma_db"
COLLECTION_NAME = "knou_chunks"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# API 키 전역 설정
genai.configure(api_key=GEMINI_API_KEY)

# ✅ Gemini 임베딩 함수 (최신 API 방식)
class GeminiEmbeddingFunction(EmbeddingFunction):
    def __init__(self):
        self.model = "models/text-embedding-004"
    
    def __call__(self, input: Documents) -> Embeddings:
        try:
            # 배치 임베딩 요청
            result = genai.embed_content(
                model=self.model,
                content=input,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"❌ 임베딩 생성 오류: {e}")
            return [[0.0] * 768 for _ in input]

class KNOUChatbot:
    def __init__(self):
        print("🤖 KNOU 챗봇을 초기화하는 중...")
        
        # ChromaDB 클라이언트 초기화
        self.chroma_client = PersistentClient(path=CHROMA_DIR)
        self.embedding_func = GeminiEmbeddingFunction()
        
        # 컬렉션 로드
        try:
            self.collection = self.chroma_client.get_collection(
                name=COLLECTION_NAME,
                embedding_function=self.embedding_func
            )
            print(f"✅ 컬렉션 로드 완료: {self.collection.count()}개 청크")
        except Exception as e:
            print(f"❌ 컬렉션 로드 실패: {e}")
            return
        
        # Gemini 생성 모델 (최신 방식)
        self.gen_model = genai.GenerativeModel("gemini-1.5-flash")
        
        print("🎯 KNOU 챗봇 준비 완료!\n")

    def _parse_date_string(self, date_str: str) -> Optional[date]:
        """Helper to parse various date string formats into a date object."""
        if not date_str:
            return None
        
        # 데이터의 주요 연도는 2025년이므로 기준으로 설정
        context_year = 2025 

        # Handle ranges, use start date
        if "~" in date_str:
            date_str = date_str.split("~")[0].strip()

        # Try common formats
        date_formats = [
            "%Y-%m-%d",      # 2025-07-16
            "%Y.%m.%d",      # 2025.07.16  
            "%Y/%m/%d",      # 2025/07/16
        ]
        
        dt_obj = None
        for fmt in date_formats:
            try:
                dt_obj = datetime.strptime(date_str, fmt).date()
                return dt_obj
            except ValueError:
                continue
        
        # Try partial formats (e.g., "07.25", "07/25")
        try:
            # "07.25" format
            if len(date_str.split('.')) == 2:
                month, day = map(int, date_str.split('.'))
                # 현재 날짜를 기준으로 연도 추정
                current_date = date.today()
                # 12월이면서 현재가 1-6월이면 작년, 아니면 올해
                if month == 12 and current_date.month <= 6:
                    year = current_date.year - 1
                # 1-6월이면서 현재가 7-12월이면 내년, 아니면 올해  
                elif month <= 6 and current_date.month >= 7:
                    year = current_date.year + 1
                else:
                    year = current_date.year
                return date(year, month, day)
            # "07/25" format
            elif len(date_str.split('/')) == 2:
                month, day = map(int, date_str.split('/'))
                # 동일한 로직 적용
                current_date = date.today()
                if month == 12 and current_date.month <= 6:
                    year = current_date.year - 1
                elif month <= 6 and current_date.month >= 7:
                    year = current_date.year + 1
                else:
                    year = current_date.year
                return date(year, month, day)
        except (ValueError, TypeError):
            pass
            
        return None

    def extract_query_date(self, query: str) -> Optional[date]:
        """Extracts a specific date (month and day) from the user query."""
        # "7월 25일", "7월25일", "7 월 25 일" etc.
        match = re.search(r'(\d{1,2})\s*월\s*(\d{1,2})\s*일', query)
        if match:
            month, day = int(match.group(1)), int(match.group(2))
            # 데이터의 주요 연도는 2025년이므로 기준으로 설정
            year = 2025 
            try:
                return date(year, month, day)
            except ValueError: # Invalid date like Feb 30
                return None
        return None

    def is_latest_query(self, query: str) -> bool:
        """사용자가 최신/최근 공지를 요청하는지 판단"""
        latest_keywords = [
            '최신', '최근', '새로운', '가장', '신규', '업데이트', 
            '이번주', '이번달', '오늘', '어제', '최신공지', '최근공지', 
            '새공지', '최신공고', '최근공고', '새공고', '최신소식'
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in latest_keywords)
    
    def get_recent_documents(self, days_back: int = 7) -> list:
        """최근 N일 이내의 문서들을 날짜순으로 가져오기"""
        try:
            today = date.today()
            cutoff_date = today - timedelta(days=days_back)
            
            all_docs_data = self.collection.get(include=["documents", "metadatas"])
            recent_docs = []
            
            for i in range(len(all_docs_data['ids'])):
                meta = all_docs_data['metadatas'][i]
                doc_date_str = meta.get('date')
                
                if doc_date_str:
                    parsed_doc_date = self._parse_date_string(doc_date_str)
                    if parsed_doc_date and parsed_doc_date >= cutoff_date:
                        recent_docs.append({
                            'id': all_docs_data['ids'][i],
                            'document': all_docs_data['documents'][i],
                            'metadata': meta,
                            'parsed_date': parsed_doc_date
                        })
            
            # 날짜순으로 정렬 (최신순)
            recent_docs.sort(key=lambda x: x['parsed_date'], reverse=True)
            
            print(f"📅 최근 {days_back}일 이내 문서: {len(recent_docs)}개 발견")
            
            if recent_docs:
                final_ids = [d['id'] for d in recent_docs[:10]]  # 상위 10개만
                final_docs = [d['document'] for d in recent_docs[:10]]
                final_metas = [d['metadata'] for d in recent_docs[:10]]
                
                return {
                    'ids': [final_ids],
                    'documents': [final_docs],
                    'metadatas': [final_metas]
                }
            
            return None
            
        except Exception as e:
            print(f"⚠️ 최근 문서 검색 중 오류: {e}")
            return None

    def get_data_date_info(self):
        """시스템 데이터의 날짜 범위 정보 가져오기"""
        try:
            all_data = self.collection.get(include=['metadatas'])
            dates = set()
            
            for meta in all_data['metadatas']:
                if meta and meta.get('date'):
                    dates.add(meta['date'])
            
            if dates:
                sorted_dates = sorted(dates)
                return {
                    'latest': sorted_dates[-1],
                    'oldest': sorted_dates[0],
                    'total_dates': len(sorted_dates)
                }
            return None
        except Exception as e:
            print(f"⚠️ 날짜 정보 가져오기 실패: {e}")
            return None

    def preprocess_query(self, query: str) -> str:
        """🚀 빠른 개선: 쿼리 전처리 - 일반 용어를 공식 용어로 변환"""
        
        # 용어 정규화 매핑
        term_mappings = {
            '학비': '등록금',
            '등록비': '등록금', 
            '학습비': '등록금',
            '납부': '등록금 납부',
            '장학': '장학금',
            '성적우수': '성적우수장학',
            '우수장학': '성적우수장학',
            '수강': '수강신청',
            '과목신청': '수강신청',
            '시험': '출석시험',
            '졸업': '졸업논문',
            '2학기': '2025학년도 2학기',
            '1학기': '2025학년도 1학기'
        }
        
        enhanced_query = query
        for original, replacement in term_mappings.items():
            if original in query and replacement not in query:
                enhanced_query = enhanced_query.replace(original, f"{original} {replacement}")
        
        return enhanced_query
    
    def get_enhanced_keywords(self, query: str) -> set:
        """🚀 빠른 개선: 대폭 확장된 키워드 매핑"""
        
        query_lower = query.lower()
        enhanced_keywords = set(query_lower.split())
        
        # 🔥 NEW: 최신성 관련 키워드 확장
        if any(word in query_lower for word in ['최신', '최근', '새로운', '가장', '신규', '업데이트', '공지', '최신공지', '최근공지', '새공지']):
            enhanced_keywords.update([
                '최신', '최근', '새로운', '신규', '업데이트', '공지',
                '최신공지', '최근공지', '새공지'
            ])
        
        # 등록금 관련 키워드 확장
        if any(word in query_lower for word in ['등록', '학비', '납부', '등록금']):
            enhanced_keywords.update([
                '등록금', '학비', '납부', '수납', '등록비', '학습비', 
                '등록금납부', '등록금안내', '등록금수납', '등록'
            ])
        
        # 장학금 관련 키워드 확장  
        if any(word in query_lower for word in ['장학', '성적우수', '성적', '우수']):
            enhanced_keywords.update([
                '장학금', '장학생', '성적우수장학', '성적우수', '장학',
                '우수장학', '장학혜택', '장학선발', '장학안내'
            ])
        
        # 수강 관련 키워드 확장
        if any(word in query_lower for word in ['수강', '과목', '신청']):
            enhanced_keywords.update([
                '수강신청', '과목신청', '수강', '과목', '신청',
                '수강안내', '신청안내', '수강방법'
            ])
        
        # 시험 관련 키워드 확장
        if any(word in query_lower for word in ['시험', '평가', '출석']):
            enhanced_keywords.update([
                '시험', '출석시험', '평가', '시험안내', '시험일정',
                '기말시험', '중간시험', '시험방법'
            ])
        
        # 시간 관련 키워드 확장
        if any(word in query_lower for word in ['2025', '2학기', '1학기']):
            enhanced_keywords.update([
                '2025학년도', '2025년', '2학기', '1학기',
                '2025학년도 2학기', '2025학년도 1학기'
            ])
        
        return enhanced_keywords
    
    def get_exact_phrases(self, query: str) -> list:
        """🚀 빠른 개선: 정확한 구문 매칭을 위한 핵심 구문 추출"""
        
        exact_phrases = []
        query_lower = query.lower()
        
        # 핵심 구문 패턴들
        key_phrases = [
            '등록금 납부', '등록금 안내', '등록금납부안내',
            '장학금 선발', '성적우수장학', '장학생 선발',
            '수강신청', '과목신청', '수강 안내',
            '시험 안내', '출석시험', '시험일정',
            '2025학년도 2학기', '2학기', '2025년 2학기'
        ]
        
        for phrase in key_phrases:
            if phrase in query_lower:
                exact_phrases.append(phrase)
        
        return exact_phrases

    def expand_query(self, query: str) -> list[str]:
        """LLM을 사용해 검색을 위한 다양한 질문 생성 (오늘 날짜 자동 포함)"""
        
        today = date.today().strftime("%Y-%m-%d")
        
        prompt = f"""당신은 벡터 검색에 최적화된 질문을 생성하는 전문가입니다. 사용자의 질문을 받아서, 그 의미를 다양한 각도에서 포착할 수 있는 3개의 구체적인 질문으로 재작성해주세요.

**중요: 오늘은 {today}입니다. 이 날짜를 기준으로 최신 정보와 관련성이 높은 질문으로 재작성해주세요.**

결과는 다른 설명 없이 번호 목록으로만 제공해주세요.

원본 질문: "{query}"

재작성된 질문:
"""
        try:
            response = self.gen_model.generate_content(prompt)
            
            expanded_queries = [line.strip().split('. ', 1)[1] for line in response.text.strip().split('\n') if '. ' in line]
            
            enhanced_query = f"[오늘: {today}] {query}"
            all_queries = [enhanced_query] + expanded_queries
            print(f"💡 쿼리 확장 (오늘: {today}): {all_queries[0]}")
            return all_queries

        except Exception as e:
            print(f"⚠️ 쿼리 확장 실패 ({e}), 원본 질문만 사용합니다.")
            enhanced_query = f"[오늘: {today}] {query}"
            return [enhanced_query]
    
    def calculate_date_weight(self, doc_date: str, current_date: str = None) -> float:
        """날짜 기반 가중치 계산 - 최신 문서일수록 높은 가중치"""
        if not current_date:
            curr_dt = date.today()
        else:
            try:
                curr_dt = datetime.strptime(current_date, "%Y-%m-%d").date()
            except ValueError:
                curr_dt = date.today()
        
        try:
            doc_dt = self._parse_date_string(doc_date)
            
            if not doc_dt:
                return 0.3  # 기본 가중치
            
            # 날짜 차이 계산 (일 단위)
            days_diff = abs((curr_dt - doc_dt).days)
            
            # 🚀 빠른 개선: 더 강력한 최신성 가중치
            if days_diff <= 7:
                return 1.5  # 최근 일주일은 더 높은 가중치
            elif days_diff <= 30:
                return 1.2  # 최근 한 달
            elif days_diff <= 90:
                return 1.0  # 최근 3개월
            elif days_diff <= 180:
                return 0.7  # 최근 6개월
            elif days_diff <= 365:
                return 0.5  # 최근 1년
            else:
                return 0.3  # 1년 이상
                
        except Exception as e:
            print(f"⚠️ 날짜 처리 오류 ({doc_date}): {e}")
            return 0.3  # 기본 가중치

    def search_documents(self, query: str, n_results: int = 5):
        """하이브리드 검색: LLM쿼리확장(Vector)과 키워드(Full-text) 검색을 RRF로 결합 + 날짜 기반 정렬"""

        # 🔥 NEW: 최신 공지 요청 우선 처리
        if self.is_latest_query(query):
            print("✨ '최신 공지' 쿼리로 감지, 최근 1주일 문서 우선 검색...")
            recent_results = self.get_recent_documents(days_back=7)
            if recent_results:
                return recent_results
            else:
                print("ℹ️ 최근 1주일 내 문서가 없어 일반 검색으로 대체합니다.")

        # 🔥 NEW: 특정 날짜 쿼리 우선 처리
        query_date = self.extract_query_date(query)
        if query_date:
            print(f"🎯 특정 날짜 쿼리 감지: {query_date.strftime('%Y-%m-%d')}")
            try:
                all_docs_data = self.collection.get(include=["documents", "metadatas"])
                
                matched_docs = []
                for i in range(len(all_docs_data['ids'])):
                    meta = all_docs_data['metadatas'][i]
                    doc_date_str = meta.get('date')
                    if doc_date_str:
                        parsed_doc_date = self._parse_date_string(doc_date_str)
                        if parsed_doc_date and parsed_doc_date == query_date:
                            matched_docs.append({
                                'id': all_docs_data['ids'][i],
                                'document': all_docs_data['documents'][i],
                                'metadata': meta
                            })
                
                if matched_docs:
                    print(f"✨ 날짜가 정확히 일치하는 {len(matched_docs)}개의 문서를 찾았습니다. 우선적으로 반환합니다.")
                    
                    final_ids = [d['id'] for d in matched_docs]
                    final_docs = [d['document'] for d in matched_docs]
                    final_metas = [d['metadata'] for d in matched_docs]
                    
                    return {
                        'ids': [final_ids],
                        'documents': [final_docs],
                        'metadatas': [final_metas]
                    }
                else:
                    print(f"ℹ️ 날짜({query_date.strftime('%Y-%m-%d')})와 일치하는 문서는 없으나, 관련 내용을 계속 검색합니다.")

            except Exception as e:
                print(f"⚠️ 특정 날짜 검색 중 오류: {e}. 일반 검색으로 대체합니다.")
        
        # 🔥 NEW: "최신" 쿼리인지 파악
        is_latest_query = any(word in query.lower() for word in ['최신', '최근', '새로운', '가장'])
        
        # 🚀 빠른 개선: 쿼리 전처리 및 키워드 확장
        enhanced_query = self.preprocess_query(query)
        
        # --- 1단계: 의미 기반 벡터 검색 (Query Expansion 사용) ---
        print("1️⃣  의미 기반 검색 실행...")
        expanded_queries = self.expand_query(enhanced_query)
        vector_search_results = {}  # {doc_id: rank}

        for i, exp_query in enumerate(expanded_queries):
            try:
                results = self.collection.query(query_texts=[exp_query], n_results=n_results)
                print(f"   벡터 검색 {i+1}: {len(results['ids'][0])}개 결과")
                for rank, doc_id in enumerate(results['ids'][0]):
                    if doc_id not in vector_search_results:
                        vector_search_results[doc_id] = rank + 1 # 랭크는 1부터 시작
            except Exception as e:
                print(f"❌ '{exp_query}' 벡터 검색 중 오류: {e}")
        
        print(f"   벡터 검색 총 {len(vector_search_results)}개 고유 문서")
        
        # --- 2단계: 강화된 키워드 기반 텍스트 검색 ---
        print("2️⃣  강화된 키워드 기반 검색 실행...")
        keyword_search_results = {} # {doc_id: rank}
        try:
            all_docs = self.collection.get(include=["documents", "metadatas"]) 
            
            # 🚀 빠른 개선: 대폭 확장된 키워드 매핑
            enhanced_keywords = self.get_enhanced_keywords(enhanced_query)
            
            print(f"🔑 확장된 키워드: {list(enhanced_keywords)[:8]}...")
            
            scores = []
            for doc_id, document, metadata in zip(all_docs['ids'], all_docs['documents'], all_docs['metadatas']):
                doc_lower = document.lower()
                title_lower = metadata.get('title', '').lower() if metadata else ''
                
                # 🚀 빠른 개선: 제목 가중치 대폭 증가 (2배 → 5배)
                content_matches = sum(1 for term in enhanced_keywords if term in doc_lower)
                title_matches = sum(1 for term in enhanced_keywords if term in title_lower) * 5  # 제목 매칭 가중치 증가
                
                # 🚀 빠른 개선: 정확한 구문 매칭 보너스
                exact_phrase_bonus = 0
                if any(phrase in title_lower for phrase in self.get_exact_phrases(enhanced_query)):
                    exact_phrase_bonus = 10  # 정확한 구문 매칭 시 높은 보너스
                
                total_score = content_matches + title_matches + exact_phrase_bonus
                
                if total_score > 0:
                    scores.append({'id': doc_id, 'score': total_score})
            
            # 점수 순으로 정렬하여 랭크 부여
            sorted_by_score = sorted(scores, key=lambda x: x['score'], reverse=True)
            for rank, item in enumerate(sorted_by_score):
                keyword_search_results[item['id']] = rank + 1
            
            print(f"   키워드 검색 총 {len(keyword_search_results)}개 문서 (상위 점수: {sorted_by_score[0]['score'] if sorted_by_score else 0})")

        except Exception as e:
            print(f"❌ 키워드 검색 중 오류: {e}")

        # --- 3단계: RRF (Reciprocal Rank Fusion) 로 결과 재정렬 ---
        print("3️⃣  RRF로 결과 재정렬...")
        fused_scores = {}
        k = 60  # RRF의 기본 상수
        vector_weight = 1.0
        keyword_weight = 2.0 # 🚀 빠른 개선: 키워드 검색 가중치 증가 (1.5 → 2.0)

        # 벡터 검색 결과 점수 합산
        for doc_id, rank in vector_search_results.items():
            fused_scores[doc_id] = fused_scores.get(doc_id, 0) + (1 / (k + rank)) * vector_weight

        # 키워드 검색 결과 점수 합산
        for doc_id, rank in keyword_search_results.items():
            fused_scores[doc_id] = fused_scores.get(doc_id, 0) + (1 / (k + rank)) * keyword_weight
            
        # 최종 점수 기준으로 정렬
        sorted_fused_ids = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)
        
        print(f"   RRF 융합 결과: {len(sorted_fused_ids)}개 문서")
        
        if not sorted_fused_ids:
            return None # 결과가 없으면 None 반환

        # 최종 상위 n_results개의 문서 정보 가져오기
        top_ids = sorted_fused_ids[:n_results]
        final_results = self.collection.get(ids=top_ids, include=["documents", "metadatas"])
        
        # --- 4단계: 날짜 기반 2차 정렬 (최신순) ---
        print("4️⃣  날짜 기반 정렬 및 가중치 적용...")
        try:
            # 오늘 날짜 자동 가져오기
            current_date = date.today().strftime("%Y-%m-%d")
            
            # id와 메타데이터를 매핑
            id_to_data = {}
            for doc_id, doc, meta in zip(final_results['ids'], final_results['documents'], final_results['metadatas']):
                date_str = meta.get('date', '1900-01-01') if meta else '1900-01-01'
                date_weight = self.calculate_date_weight(date_str, current_date)
                
                # RRF 점수에 날짜 가중치 적용
                weighted_score = fused_scores[doc_id] * date_weight
                
                id_to_data[doc_id] = {
                    'document': doc,
                    'metadata': meta,
                    'date': date_str,
                    'rrf_score': fused_scores[doc_id],
                    'date_weight': date_weight,
                    'final_score': weighted_score
                }
            
            # 🔥 NEW: '최신' 쿼리일 경우 날짜 우선 정렬, 아닐 경우 기존 점수 정렬
            if is_latest_query:
                print("✨ '최신' 쿼리로 감지, 날짜 우선 정렬 실행...")
                # 날짜 문자열로 직접 정렬 (대부분의 YYYY-MM-DD 형식에서 동작)
                # 동일 날짜의 경우 기존 점수로 2차 정렬
                sorted_ids = sorted(
                    top_ids,
                    key=lambda x: (id_to_data.get(x, {}).get('date', '1900-01-01'), id_to_data.get(x, {}).get('final_score', 0)),
                    reverse=True
                )
            else:
                # 최종 가중 점수로 정렬 (높은 점수 순)
                sorted_ids = sorted(
                    top_ids,
                    key=lambda x: id_to_data[x]['final_score'],
                    reverse=True
                )
            
            # 정렬된 순서로 결과 재구성
            final_docs = [id_to_data[doc_id]['document'] for doc_id in sorted_ids]
            final_metas = [id_to_data[doc_id]['metadata'] for doc_id in sorted_ids]
            
            # 점수 정보 출력 (디버깅용) - 모바일 최적화: 간략하게
            print(f"📊 기준일: {current_date}, 상위 문서 점수:")
            for i, doc_id in enumerate(sorted_ids[:2]):  # 상위 2개만
                data = id_to_data[doc_id]
                print(f"   {i+1}. 최종: {data['final_score']:.4f} [{data['date']}]")
            
            return {
                'ids': [sorted_ids],
                'documents': [final_docs],
                'metadatas': [final_metas]
            }
            
        except Exception as e:
            print(f"⚠️ 날짜 정렬 중 오류 ({e}), RRF 순서 유지")
            # 오류 시 기존 RRF 순서 유지
            id_to_doc = {doc_id: (doc, meta) for doc_id, doc, meta in zip(final_results['ids'], final_results['documents'], final_results['metadatas'])}
            final_docs = [id_to_doc[doc_id][0] for doc_id in top_ids if doc_id in id_to_doc]
            final_metas = [id_to_doc[doc_id][1] for doc_id in top_ids if doc_id in id_to_doc]
            
            return {
                'ids': [top_ids],
                'documents': [final_docs],
                'metadatas': [final_metas]
            }
    
    def generate_answer(self, query: str, context_docs: list, context_metas: list = None):
        """검색된 문서를 바탕으로 답변 생성 (스트리밍 및 안전 설정 완화)"""
        
        context_parts = []
        for i, doc in enumerate(context_docs):
            if context_metas and i < len(context_metas) and context_metas[i]:
                date_val = context_metas[i].get('date', '날짜 미상')
                title = context_metas[i].get('title', '제목 없음')
                context_parts.append(f"문서 제목: {title}\n문서 날짜: {date_val}\n문서 내용:\n{doc}")
            else:
                context_parts.append(doc)
        
        context = "\n\n---\n\n".join(context_parts)
        
        today_str = date.today().strftime("%Y년 %m월 %d일")
        
        prompt = f"""당신은 한국방송통신대학교(KNOU)의 정보를 가장 가독성 좋게 요약하는 AI 전문가입니다. **반드시 마크다운(Markdown)을 사용**하여, 핵심을 먼저 보여주고 세부 정보를 명확하게 구분하여 사용자가 쉽게 이해하도록 답변을 구성해주세요.

**중요: 오늘은 {today_str}입니다. 이 날짜를 기준으로 최신성과 관련성을 판단해주세요.**

**답변 생성 규칙 (Markdown 사용):**

1.  **🎯 핵심 요약 (맨 처음에):**
    *   사용자 질문에 대한 가장 중요한 답변을 **굵은 글씨**와 함께 1~2문장으로 요약하여 가장 먼저 보여주세요.
    *   관련 공지 날짜를 반드시 언급해주세요. (예: "**2025년 7월 16일 공지에 따르면, 2학기 성적우수장학생 선발이 확정되었습니다.**")
    *   최신 공지를 요청받은 경우, 오늘 날짜 기준으로 가장 최근 공지들을 날짜순으로 나열해주세요.

2.  **🔖 주요 정보 (섹션으로 구분):**
    *   `###` (h3)와 이모지를 사용하여 주요 정보 섹션을 나누세요. (예: `### 📌 선발 확인 방법`)
    *   내용은 `*`를 사용한 목록(list)으로 간결하게 설명하세요.
    *   표(Table)는 마크다운 표 문법을 사용하여 간결하게 만드세요.

3.  **⭐ 강조:**
    *   가장 중요한 정보는 `**굵게**` 표시하여 강조하세요.

4.  **친절한 말투:**
    *   전체적으로 친근하고 명확한 말투를 사용하세요.

5.  **정보의 정확성:**
    *   제공된 **참고 문서** 내용만을 바탕으로 답변해야 합니다. 없는 내용은 "정보를 찾을 수 없습니다"라고 명확히 말해주세요.

---

**사용자 질문:** {query}

**참고 문서:**
{context}

**답변 (Markdown 형식):**
"""

        try:
            # 안전 설정 완화 및 스트리밍 활성화
            response = self.gen_model.generate_content(
                prompt,
                stream=True,
                safety_settings={
                    'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                    'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                    'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                    'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
                }
            )
            for chunk in response:
                yield chunk.text
        except Exception as e:
            print(f"❌ 답변 생성 중 오류: {e}")
            yield "죄송합니다, 답변을 생성하는 동안 오류가 발생했습니다."

    def chat(self, query: str):
        """전체 RAG 프로세스 실행 (스트리밍 답변 생성)"""
        print(f"🔍 검색 중: '{query}'")
        
        # 1. 관련 문서 검색
        search_results = self.search_documents(query)
        if not search_results or not search_results['documents'][0]:
            yield "죄송합니다. 관련된 정보를 찾을 수 없습니다."
            return

        # 2. 검색 결과 출력
        documents = search_results['documents'][0]
        metadatas = search_results.get('metadatas', [None])[0] if search_results.get('metadatas') else None
        print(f"📚 {len(documents)}개의 관련 문서를 찾았습니다.")
        
        # 3. 답변 생성 (스트리밍)
        print("💭 스트리밍 답변 생성 중...")
        yield from self.generate_answer(query, documents, metadatas)
        print("\n✅ 스트리밍 완료.")

def main():
    """메인 함수"""
    try:
        chatbot = KNOUChatbot()
        # chatbot.interactive_chat() # 이제 스트리밍 사용
        # 스트리밍 사용 시 예시:
        # for answer_chunk in chatbot.chat("오늘 학교 출석 체크 방법은?"):
        #     print(answer_chunk, end='', flush=True)
        # print() # 마지막 줄 출력

        # 대화형 인터페이스 유지 - 이 줄을 주석 처리하세요!
        # chatbot.interactive_chat()
        
        print("✅ 챗봇이 준비되었습니다. FastAPI 서버를 통해 사용하세요.")

    except Exception as e:
        print(f"❌ 챗봇 초기화 실패: {e}")

if __name__ == "__main__":
    main() 