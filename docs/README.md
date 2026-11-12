# docs/

Drop the PDFs you want the agent to answer from here — `ingest.py` reads `docs/*.pdf`.

For the demo, generate ready-made sample docs (refund / shipping / warranty, with
page-locatable facts):

```bash
pip install reportlab
python ../make_sample_pdfs.py   # or run from the repo root: python make_sample_pdfs.py
```
