import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Ellipse, FancyArrowPatch
matplotlib.rcParams.update({"font.family":"serif","font.serif":["Times New Roman","Times","Nimbus Roman","STIXGeneral","Liberation Serif","DejaVu Serif"],
 "mathtext.fontset":"stix","font.size":8,"svg.fonttype":"none","savefig.pad_inches":0.02})
K="#000000"; LW=0.6
C_FREE="#56B4E9"; C_SP="#E6E6E6"; C_FIX="#0072B2"; E=0.32  # ellipse y/x ratio (perspective)

def cyl(ax,y0,h,r,fc,z):
    t=np.linspace(np.pi,2*np.pi,60)
    bot=np.c_[r*np.cos(t),y0+E*r*np.sin(t)]
    side=np.vstack([[-r,y0+h],bot,[r,y0+h]])
    ax.add_patch(Polygon(side,closed=True,fc=fc,ec=K,lw=LW,zorder=z))
    ax.add_patch(Ellipse((0,y0+h),2*r,2*E*r,fc=fc,ec=K,lw=LW,zorder=z+0.1))

def arr(ax,x,y,dx,dy,c,z,lw=0.7,ms=5):
    ax.add_patch(FancyArrowPatch((x,y),(x+dx,y+dy),arrowstyle="-|>",mutation_scale=ms,lw=lw,color=c,zorder=z,shrinkA=0,shrinkB=0))

fig,ax=plt.subplots(figsize=(3.5,2.6))
R=1.5  # 30 nm disc (10 nm per unit)
yb=-1.2; hb=0.9; yfix=yb+hb; hfix=0.8; ysp=yfix+hfix; hsp=0.25; yfr=ysp+hsp; hfr=0.8; yt=yfr+hfr; ht=0.9
cyl(ax,yfix,hfix,R,C_FIX,2)
for x in np.linspace(-1.2,1.2,7):
    arr(ax,x,yfix-E*R*np.sqrt(max(0,1-(x/R)**2))+0.12,0,0.5,"white",2.5)
cyl(ax,ysp,hsp,R,C_SP,3)
cyl(ax,yfr,hfr,R,C_FREE,4)
rng=np.random.default_rng(3)
for x in np.linspace(-1.15,1.15,7):
    th=rng.uniform(0,2*np.pi); L=0.32
    yc=yfr+hfr/2-E*R*np.sqrt(max(0,1-(x/R)**2))*0.6
    arr(ax,x-L*np.cos(th)/2,yc-L*np.sin(th)/2,L*np.cos(th),L*np.sin(th),K,4.5,lw=0.6,ms=4)
# current arrows (downwards through the stack, as on poster)
arr(ax,0,yt+0.95,0,-0.7,K,6,lw=1.0,ms=8)
arr(ax,0,yfix-E*R-0.1,0,-0.7,K,6,lw=1.0,ms=8)
ax.text(0.15,yfix-E*R-0.45,r"$I$ (current pulse)",va="center",ha="left")
# left labels
xl=-2.05
for y,s in [(yfr+hfr*0.4,"Free layer"),(ysp+hsp*0.3,"Spacer layer"),(yfix+hfix*0.4,"Fixed layer")]:
    xe=-R
    ax.plot([xl+0.05,xe],[y,y],color=K,lw=0.4,zorder=7); ax.plot([xe],[y],"o",ms=1.6,color=K,zorder=7)
    ax.text(xl,y,s,ha="right",va="center")
# right dimension labels
xr=2.0
def dim(y,s): ax.text(xr,y,s,ha="left",va="center")
dim(yfr+hfr*0.4,r"$\varnothing$ 30 nm, $t$ = 2.6 nm, $\mathbf{m}$ free")
dim(yfix+hfix*0.4,r"$\mathbf{p}$ = $+\hat{z}$ (fixed)")
for y in [yfr+hfr*0.4,yfix+hfix*0.4]:
    xe=R
    ax.plot([xe,xr-0.05],[y,y],color=K,lw=0.4,ls=(0,(2,2)),zorder=7)
# z axis
ax.add_patch(FancyArrowPatch((-3.3,yfix-1.3),(-3.3,yfix-0.6),arrowstyle="-|>",mutation_scale=6,lw=0.6,color=K))
ax.text(-3.2,yfix-0.7,r"$z$",ha="left",va="bottom")
ax.set_xlim(-3.6,4.2); ax.set_ylim(yfix-1.4,yt+1.05); ax.set_aspect("equal"); ax.axis("off")
import os; os.makedirs("plots",exist_ok=True); o="plots/paper_device_diagram"
fig.savefig(o+".svg",bbox_inches="tight",facecolor="white"); fig.savefig(o+".png",dpi=300,bbox_inches="tight",facecolor="white")
