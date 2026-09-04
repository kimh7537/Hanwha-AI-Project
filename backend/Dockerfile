# 배포용 이미지.
#
# 파이썬 런타임만으로 충분하지 않은 이유는 하나다 — 원본↔결과 슬라이드 이미지 대조.
# 그 렌더링을 윈도우에서는 설치된 PowerPoint 가 하는데 리눅스 서버에는 없어서,
# LibreOffice 를 이미지에 함께 담는다(app/services/render_slides.py).
FROM python:3.12-slim

# libreoffice-impress: PPTX → PDF. PDF → PNG 는 이미 의존성인 PyMuPDF 가 그린다.
#
# 폰트가 왜 이만큼 필요한가. LibreOffice 는 없는 폰트를 fontconfig 가 고르는 아무 폰트로
# 바꾸고, 글자 폭이 원본과 다르면 상자에 맞춰 짜 둔 글이 그대로 줄바꿈된다. 실제로
# 한글만 깔아 둔 동안 배포에서 '92,929' 가 '92,92 / 9' 로 쪼개져 나왔다 — 한글이 아니라
# 숫자가 넘친 것이다(나눔고딕의 숫자는 맑은 고딕보다 11~12% 넓다).
#
# fonts-noto-cjk: 맑은 고딕 자리를 받는다. 숫자 폭 오차가 1~3% 로 가장 가깝다.
# fonts-liberation / carlito / caladea: Arial·Times New Roman·Calibri·Cambria 의
#   폭이 똑같은 대체본이다. fontconfig 의 30-metric-aliases.conf 가 알아서 이어 주므로
#   설치만 하면 된다. 이 자료 하나에도 Times New Roman 이 535 곳 쓰인다.
# fonts-nanum: 위 폰트에 없는 글자를 위한 마지막 받침.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libreoffice-impress \
        fonts-noto-cjk \
        fonts-liberation \
        fonts-crosextra-carlito \
        fonts-crosextra-caladea \
        fonts-nanum \
    && rm -rf /var/lib/apt/lists/*

# 어느 폰트로 바뀔지를 우연에 맡기지 않는다. 규칙과 근거는 파일 안에 있다.
COPY fonts-substitutes.conf /etc/fonts/conf.d/99-audiencedeck-substitutes.conf
RUN fc-cache -f

WORKDIR /app

# 소스보다 먼저 복사한다. 코드만 바뀐 재배포에서 설치 층을 다시 만들지 않는다.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 로그가 버퍼에 묶여 있으면 Render 대시보드에 늦게 뜬다.
ENV PYTHONUNBUFFERED=1

# $PORT 는 Render 가 준다. 치환이 필요하므로 쉘 형식으로 둔다.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
