# HIS Mode Choice — Control Form System

A Streamlit web app for auto-filling GPS points into Household Interview Survey control forms.

## Features
- 📊 **Dashboard** — Track usage, remaining points, and generation history per city
- 📝 **Generate Forms** — Auto-fill #, Stratum, and GPS Coordinates (lat, lon)
- 📄 **View & Print** — Preview all forms, print directly, or download as HTML
- 🔒 **No duplicates** — Points are assigned sequentially; used points are persisted in `data/usage.json`
- ⚙️ **Configurable** — Set points per form (default: 6) from the sidebar

## Cities
| City | Points |
|------|--------|
| Laoag City (Capital) | 1,800 |
| La Union – San Fernando | 3,200 |

## Local Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Community Cloud

1. Push this folder to a **GitHub repository**
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app** → connect your GitHub repo
4. Set **Main file path** to `app.py`
5. Click **Deploy**

> **Note:** The `data/usage.json` file (tracking used points) is stored locally. On Streamlit Cloud, this resets on each deployment. For persistent tracking across deployments, replace `usage.json` with a database (e.g., Streamlit's built-in `st.secrets` + a free Supabase/Neon DB).

## File Structure

```
his_app/
├── app.py                   # Main Streamlit application
├── requirements.txt         # Python dependencies
├── .streamlit/
│   └── config.toml          # Theme & server settings
└── data/
    ├── laoag.csv            # Laoag GPS points (1,800 rows)
    ├── launion.csv          # La Union GPS points (3,200 rows)
    └── usage.json           # Auto-generated: tracks used points
```
