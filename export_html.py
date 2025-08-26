import html

def build_html_export(available_series) -> bytes:
    groups = {
        "Creative": ["Creative - Designer", "Creative - Writer"],
        "PR": ["PR - Traditional", "PR - Social"],
        "Strategy": ["Strategy"],
        "Tech": ["Tech - Front-end", "Tech - Back-end"],
        "Video": ["Video"],
    }

    def cell(col_name):
        items = []
        total = 0
        for d in groups[col_name]:
            count = int(available_series.get(d, 0))
            items.append(f"<div class='row'><span class='name'>{html.escape(d)}</span>: <span class='num'>{count}</span></div>")
            total += count
        if len(groups[col_name]) > 1:
            items.append(f"<div class='row total'><strong>{col_name} Total: {total}</strong></div>")
        return "".join(items)

    html_doc = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8' />
<title>Hart Legend & Staff Table</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; padding: 24px; }}
  .legend {{ border: 1px solid #000; border-radius: 8px; padding: 12px; }}
  .legend h2 {{ margin: 0 0 12px 0; font-size: 18px; }}
  .cols {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; }}
  .name {{ font-weight: 500; }}
  .row {{ margin: 4px 0; }}
  .row.total {{ margin-top: 8px; }}
  .num {{ font-variant-numeric: tabular-nums; }}
</style>
</head>
<body>
  <div class='legend'>
    <h2>Current Staff Availability</h2>
    <div class='cols'>
      <div>
        <div class='col-title'><strong>Creative</strong></div>
        {cell("Creative")}
      </div>
      <div>
        <div class='col-title'><strong>PR</strong></div>
        {cell("PR")}
      </div>
      <div>
        <div class='col-title'><strong>Strategy</strong></div>
        {cell("Strategy")}
      </div>
      <div>
        <div class='col-title'><strong>Tech</strong></div>
        {cell("Tech")}
      </div>
      <div>
        <div class='col-title'><strong>Video</strong></div>
        {cell("Video")}
      </div>
    </div>
  </div>
</body>
</html>
""".encode("utf-8")
    return html_doc
