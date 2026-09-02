# 배포용 이미지.
#
# 파이썬 런타임만으로 충분하지 않은 이유는 하나다 — 원본↔결과 슬라이드 이미지 대조.
# 그 렌더링을 윈도우에서는 설치된 PowerPoint 가 하는데 리눅스 서버에는 없어서,
# LibreOffice 를 이미지에 함께 담는다(app/services/render_slides.py).
FROM python:3.12-slim

# libreoffice-impress: PPTX → PDF. PDF → PNG 는 이미 의존성인 PyMuPDF 가 그린다.
# fonts-nanum: 이것이 없으면 슬라이드의 한글이 전부 네모로 나온다. 대조가 목적이라 필수다.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libreoffice-impress fonts-nanum \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 소스보다 먼저 복사한다. 코드만 바뀐 재배포에서 설치 층을 다시 만들지 않는다.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 로그가 버퍼에 묶여 있으면 Render 대시보드에 늦게 뜬다.
ENV PYTHONUNBUFFERED=1

# $PORT 는 Render 가 준다. 치환이 필요하므로 쉘 형식으로 둔다.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
