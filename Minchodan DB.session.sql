-- 1. 데이터베이스 내의 테이블 목록 조회
SHOW TABLES;

-- 2. 데이터베이스 인코딩 및 정렬 규칙 확인
SHOW VARIABLES LIKE 'character_set_database';
SHOW VARIABLES LIKE 'collation_database';

-- 3. (선택) 특정 테이블의 데이터를 조회하고 싶을 때 아래 쿼리의 테이블명을 변경하여 실행하십시오.
-- SELECT * FROM 테이블명 LIMIT 10;
