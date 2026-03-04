#!/usr/bin/env python3
"""
최소한의 대시보드 서버 - CORS 완전 지원
"""

import json
import os
import http.server
import socketserver
from datetime import datetime

PORT = 8080

class MinimalHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
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
            # 정적 파일 서빙
            super().do_GET()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def serve_index(self):
        html = '''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>트레이더 마크 📊</title>
<style>
body { font-family: sans-serif; padding: 20px; }
h1 { color: #333; }
.data { background: #f5f5f5; padding: 20px; border-radius: 10px; }
</style>
</head>
<body>
<h1>트레이더 마크 📊 - 대시보드</h1>
<div id="data">데이터 로딩 중...</div>
<script>
async function load() {
    const res = await fetch('/api/portfolio');
    const data = await res.json();
    document.getElementById('data').innerHTML = `
        <h3>💰 현재 자본: ${data.capital.toLocaleString()}원</h3>
        <p>📊 총 거래: ${data.trade_log.length}회</p>
        <p>🕒 업데이트: ${data.last_updated}</p>
    `;
}
load();
</script>
</body>
</html>'''
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(html))
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def serve_portfolio(self):
        try:
            with open('paper_portfolio.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.send_json(data)
        except Exception as e:
            self.send_json({'error': str(e)}, 500)
    
    def serve_health(self):
        self.send_json({
            'status': 'ok',
            'server': '트레이더마크 대시보드',
            'time': datetime.now().isoformat()
        })
    
    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(body)
    
    def log_message(self, format, *args):
        pass  # 로그 생략

def main():
    os.chdir(os.path.dirname(__file__))
    
    with socketserver.TCPServer(("0.0.0.0", PORT), MinimalHandler) as httpd:
        print(f"🚀 트레이더 마크 대시보드 시작: http://localhost:{PORT}")
        print(f"🌐 네트워크 접속: http://{get_ip()}:{PORT}")
        print("=" * 50)
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 대시보드 종료")

def get_ip():
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