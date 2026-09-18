"""Plot all corrected P6 outcomes from original API chunks."""
import json
from collections import Counter
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

out=Path(__file__).resolve().parents[1]/'results/hardware/p6_chunk_audit_20260907'
shots=json.loads((out/'shots_400.json').read_text())
counts=sorted(Counter(shots).values(),reverse=True)
assert len(shots)==400 and len(counts)==400 and set(counts)=={1}
fig,ax=plt.subplots(figsize=(10,4))
ax.bar(range(1,401),counts,width=1,color='#3178a8')
ax.set(xlabel='Distinct bitstring rank (all tied)',ylabel='Observed count',ylim=(0,1.5),xlim=(0,401),title='P6: corrected frequency distribution — all 400 outcomes')
ax.set_yticks([0,1]);ax.text(200,1.15,'400 distinct strings; each observed once',ha='center')
fig.text(.5,.01,'Original API chunks parsed separately; SDK-added duplicate frames excluded by construction.',ha='center',fontsize=9)
fig.tight_layout(rect=(0,.04,1,1));fig.savefig(out/'corrected_frequency.png',dpi=160);fig.savefig(out/'corrected_frequency.pdf')
