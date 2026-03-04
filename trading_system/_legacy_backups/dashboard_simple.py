#!/usr/bin/env python3
"""
트레이더 마크 📊 - 간단한 대시보드 서버
CORS 완전 지원 + 실시간 업데이트
"""

import json
import os
import http.server
import socketserver
from datetime import datetime
from pathlib import Path

PORT = 8888
BASE_DIR = Path(__file__).parent

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """대시보드 핸들러"""
    
    def do_GET(self):
        """GET 요청 처리"""
        # CORS 헤더
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        
        if self.path == '/' or self.path == '':
            self.serve_index()
        elif self.path == '/api/portfolio':
            self.serve_portfolio()
        elif self.path == '/api/health':
            self.serve_health()
        else:
            super().do_GET()
    
    def do_OPTIONS(self):
        """CORS preflight 처리"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def serve_index(self):
        """인덱스 페이지"""
        html = '''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>트레이더 마크 📊</title>
<style>
body { font-family: sans-serif; padding: 20px; background: #f5f5f5; }
.container { max-width: 1200px; margin: 0 auto; }
.header { text-align: center; margin-bottom: 30px; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
.kpi-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
.table { width: 100%; background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 10px; text-align: left; border-bottom: 1px solid #eee; }
.profit { color: green; }
.loss { color: red; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>트레이더 마크 📊 - 실시간 모의투자</h1>
    <p id="timestamp">로딩 중...</p>
  </div>
  
  <div class="kpi-grid" id="kpiGrid">
    <div class="kpi-card"><div>💰 현재 자본</div><div id="capital" style="font-size: 24px; font-weight: bold;">-</div></div>
    <div class="kpi-card"><div>📈 수익률</div><div id="returnRate" style="font-size: 24px; font-weight: bold;">-</div></div>
    <div class="kpi-card"><div>📊 총 거래</div><div id="tradeCount" style="font-size: 24px; font-weight: bold;">-</div></div>
    <div class="kpi-card"><div>🎯 승률</div><div id="winRate" style="font-size: 24px; font-weight: bold;">-</div></div>
  </div>
  
  <div class="table">
    <h3>📈 최근 거래 (10건)</h3>
    <table id="tradeTable">
      <thead><tr><th>시간</th><th>종목</th><th>매매</th><th>가격</th><th>손익</th></tr></thead>
      <tbody id="tradeBody"></tbody>
    </table>
    <button onclick="loadData()" style="margin-top: 15px; padding: 10px 20px;">새로고침</button>
    <button onclick="startAutoRefresh()" style="margin-top: 15px; padding: 10px 20px;">자동 새로고침 시작</button>
  </div>
</div>

<script>
async function loadData() {
    try {
        const res = await fetch('/api/portfolio');
        const data = await res.json();
        updateDisplay(data);
    } catch(e) {
        console.error('오류:', e);
    }
}

function updateDisplay(data) {
    // 자본
    const capital = data.capital || 0;
    const initial = 1000000;
    const returnPct = ((capital - initial) / initial * 100).toFixed(2);
    document.getElementById('capital').textContent = capital.toLocaleString() + '원';
    document.getElementById('returnRate').textContent = returnPct + '%';
    document.getElementById('returnRate').style.color = returnPct >= 0 ? 'green' : 'red';
    
    // 거래
    const trades = data.trade_log || [];
    document.getElementById('tradeCount').textContent = trades.length + '회';
    
    // 승률
    const wins = trades.filter(t => (t.profit || 0) > 0).length;
    const winRate = trades.length > 0 ? ((wins / trades.length) * 100).toFixed(1) : 0;
    document.getElementById('winRate').textContent = winRate + '%';
    
    // 거래 테이블
    const recent = trades.slice(-10).reverse();
    let html = '';
    recent.forEach(t => {
        const time = new Date(t.date).toLocaleTimeString();
        const profit = t.profit || 0;
        html += `<tr>
            <td>${time}</td>
            <td>${t.symbol}</td>
            <td>${t.side === 'BUY' ? '🟢 매수' : '🔴 매도'}</td>
            <td>${(t.price || 0).toLocaleString()}원</td>
            <td class="${profit >= 0 ? 'profit' : 'loss'}">${profit >= 0 ? '+' : ''}${profit.toFixed(1)}원</td>
        </tr>`;
    });
    document.getElementById('tradeBody').innerHTML = html || '<tr><td colspan="5">거래 없음</td></tr>';
    
    // 타임스탬프
    document.getElementById('timestamp').textContent = 
        `마지막 업데이트: ${new Date(data.last_updated || Date.now()).toLocaleString()}`;
}

let refreshInterval = null;
function startAutoRefresh(sec = 10) {
    if (refreshInterval) clearInterval(refreshInterval);
    loadData();
    refreshInterval = setInterval(loadData, sec * 1000);
    alert(`${sec}초마다 자동 새로고침 시작`);
}

// 초기 로드
loadData();
</script>
</body>
</html>'''
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(html.encode('utf-8')))
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def serve_portfolio(self):
        """포트폴리오 데이터"""
        try:
            file_path = BASE_DIR / 'paper_portfolio.json'
            if not file_path.exists():
                self.send_json({'error': '파일 없음'}, 404)
                return
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.send_json(data)
            
        except Exception as e:
            self.send_json({'error': str(e)}, 500)
    
    def serve_health(self):
        """헬스 체크"""
        self.send_json({
            'status': 'ok',
            'time': datetime.now().isoformat(),
            'server': '트레이더마크 대시보드'
        })
    
    def send_json(self, data, status=200):
        """JSON 응답"""
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.end_headers()
        self.wfile.write(body)
    
    def log_message(self, format, *args):
        """로그 간소화"""
        pass

def main():
    """메인 함수"""
    os.chdir(BASE_DIR)
    
    with socketserver.TCPServer(("0.0.0.0", PORT), DashboardHandler) as httpd:
        print(f"🚀 트레이더 마크 대시보드 시작")
        print(f"📍 로컬: http://localhost:{PORT}")
        print(f"🌐 네트워크: http://{get_ip()}:{PORT}")
        print(f"📊 API: http://localhost:{PORT}/api/portfolio")
        print("=" * 50)
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 대시보드 종료")

def get_ip():
    """로컬 IP 가져오기"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

if __name__ == '__main__':
    main()