from pathlib import Path
p=Path('app/static/style.css')
s=p.read_bytes()
# Do not apply text-display rules to the date-list layout container.
s=s.replace(b'[data-apartment-inspection-display] > span:not(.status-pill)', b'[data-apartment-inspection-display] > span:not(.status-pill):not(.apartment-inspection-date-stack)')
start=s.index(b'/* Inspection dates use a separate')
a=s[:start]; t=s[start:]
t=t.replace(b'grid-template-columns: minmax(4.8rem, 5.6rem) minmax(0, 1fr)', b'grid-template-columns: minmax(4.8rem, 40%) minmax(0, 1fr)')
t=t.replace(b'grid-template-columns: auto minmax(0, 1fr)', b'grid-template-columns: minmax(0, 1fr)')
# Stack status above saved dates; align controls with same column.
t=t.replace(b'grid-column: 2 !important;\n  grid-row: 1 !important;\n  flex-direction:', b'grid-column: 1 !important;\n  grid-row: 2 !important;\n  flex-direction:')
t=t.replace(b'width: 50% !important;', b'width: 100% !important;')
t=t.replace(b'margin: 0 0 0 3.25rem !important;', b'margin: 0 !important;')
t=t.replace(b'row-gap: .36rem !important;', b'row-gap: .5rem !important;')
t=t.replace(b'border-radius: 999px !important;', b'border-radius: .65rem !important;')
t=t.replace(b'padding: .16rem .24rem .16rem .55rem !important;', b'padding: .3rem .4rem .3rem .65rem !important;')
# Set list grid position explicitly, including files with CRLF.
t=t.replace(b'grid-auto-flow: row !important;', b'grid-auto-flow: row !important;\n  grid-column: 1 !important;\n  grid-row: 2 !important;')
p.write_bytes(a+t)
p=Path('app/templates/base.html'); s=p.read_bytes().replace(b'v696-inspection-dates-grid',b'v697-inspection-layout'); p.write_bytes(s)
