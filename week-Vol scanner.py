import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 設定網頁標題與排版
st.set_page_config(
    page_title="周K Vol 篩選器 (受保護)",
    page_icon="📊",
    layout="centered"
)

# --- 密碼保護功能 ---
def check_password():
    """如果密碼正確則回傳 True，否則顯示輸入框並回傳 False"""
    def password_entered():
        if st.session_state["password"] == "592888":  # 👈 在這裡設定您的專屬密碼！
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # 刪除暫存密碼以策安全
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # 第一次進入，顯示輸入密碼畫面
        st.title("🔒 系統安全驗證")
        st.text_input(
            "請輸入密碼以存取周K Vol 篩選器：",
            type="password",
            on_change=password_entered, 
            key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # 密碼輸入錯誤，重新顯示輸入框與錯誤訊息
        st.title("🔒 系統安全驗證")
        st.text_input(
            "請輸入密碼以存取周K Vol 篩選器：",
            type="password",
            on_change=password_entered,
            key="password"
        )
        st.error("❌ 密碼錯誤，請重新輸入！")
        return False
    else:
        # 密碼正確
        return True

# 只有密碼驗證通過，才顯示後續的 App 內容
if check_password():

    # --- 核心計算與成交量篩選邏輯 ---
    def compute_volume_ma(df, ma_period=20):
        vol_col = None
        for col in ['Volume', 'volume']:
            if col in df.columns:
                vol_col = col
                break
        if vol_col is None:
            raise ValueError("找不到成交量欄位 (Volume)")
        
        df['Vol_MA'] = df[vol_col].rolling(window=ma_period).mean()
        df['Vol_Ratio'] = df[vol_col] / df['Vol_MA']
        return df, vol_col

    def scan_weekly_volume_stocks(ticker_list, target_date, ma_period=20, min_mult=1.5, max_mult=3.0):
        result = []
        target_dt = pd.Timestamp(target_date)
        target_year_week = target_dt.to_period('W')
        start_date = (target_dt - pd.Timedelta(days=365*2)).strftime('%Y-%m-%d')
        end_date = (target_dt + pd.Timedelta(days=14)).strftime('%Y-%m-%d')

        for ticker in ticker_list:
            try:
                df = yf.download(ticker, start=start_date, end=end_date, interval="1wk", auto_adjust=False, progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df = df.dropna(subset=["Close"])
                if len(df) < (ma_period + 5): continue
                
                df, vol_col = compute_volume_ma(df, ma_period)
                
                df_periods = df.index.to_period('W')
                valid_mask = df_periods <= target_year_week
                if not valid_mask.any(): continue
                
                target_idx = df[valid_mask].index[-1]
                target_row = df.loc[target_idx]
                
                current_vol = float(target_row[vol_col])
                vol_ma = float(target_row['Vol_MA'])
                vol_ratio = float(target_row['Vol_Ratio'])
                
                if pd.notna(vol_ratio) and (min_mult <= vol_ratio <= max_mult):
                    result.append({
                        'ticker': ticker,
                        'vol': current_vol,
                        'ma_vol': vol_ma,
                        'ratio': vol_ratio
                    })
            except:
                pass
        return result

    # --- App 主介面 ---
    st.title("📊 周K 成交量 (Vol) 篩選器")
    st.write("歡迎回來！請自訂下方的週數與倍數篩選標準：")

    default_tickers = "2330, 1519, 2603, 2605"
    tickers_input = st.text_area(
        "輸入股票代號 (支援空格、逗號、換行分隔):",
        value=default_tickers,
        height=100
    )

    # 建立滑桿控制區
    st.subheader("⚙️ 參數設定")
    ma_period = st.slider("均量週數 (MA 週數)", min_value=5, max_value=60, value=20, step=5)
    
    col_min, col_max = st.columns(2)
    with col_min:
        min_mult = st.slider("最小倍數", min_value=0.5, max_value=5.0, value=1.5, step=0.1)
    with col_max:
        max_mult = st.slider("最大倍數", min_value=1.0, max_value=10.0, value=3.0, step=0.1)

    col1, col2 = st.columns([2, 1])
    with col1:
        target_date = st.date_input("選擇基準日期:", datetime.now())
    with col2:
        st.write("")
        st.write("")
        run_button = st.button("🎯 開始篩選", use_container_width=True)

    if run_button:
        if min_mult > max_mult:
            st.error("❌ 錯誤：最小倍數不能大於最大倍數！")
        else:
            with st.spinner("⏳ 正在分析交易量數據，請稍候..."):
                raw_input = tickers_input
                for char in [',', ';', '\n', '\t', '，', '；']:
                    raw_input = raw_input.replace(char, ' ')
                cleaned_tickers = [t.strip() for t in raw_input.split(' ') if t.strip()]

                if not cleaned_tickers:
                    st.warning("⚠️ 請輸入至少一個股票代號！")
                else:
                    formatted_tickers = [f"{t}.TW" if "." not in t else t for t in cleaned_tickers]
                    results = scan_weekly_volume_stocks(
                        formatted_tickers, 
                        target_date.strftime('%Y-%m-%d'),
                        ma_period=ma_period,
                        min_mult=min_mult,
                        max_mult=max_mult
                    )

                    st.subheader("🎉 篩選結果")
                    st.metric(label="掃描個股數量", value=f"{len(formatted_tickers)} 檔")

                    if results:
                        st.success(f"✅ 符合條件的股票 ({len(results)} 檔):")
                        
                        # 轉換為 DataFrame 美化表格顯示
                        df_res = pd.DataFrame(results)
                        df_res.columns = ['股票代號', '當週成交量', f'{ma_period}週均量', '成交量倍數']
                        df_res['成交量倍數'] = df_res['成交量倍數'].map(lambda x: f"{x:.2f} 倍")
                        st.dataframe(df_res, use_container_width=True)
                        
                        results_str = ", ".join([r['ticker'] for r in results])
                        st.code(results_str, language="text")
                        st.info("💡 提示：點擊上方代號框右上角的『📋』圖示即可快速複製！")
                    else:
                        st.error("❌ 查無符合成交量篩選條件的周K個股。")
