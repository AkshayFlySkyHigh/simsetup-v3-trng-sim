# Simulation setup flow, laid out as on the poster panel "The Simulation Setup (Simplified)".
# Coordinates are the poster panel's pixel positions (y down), so relative block positions match.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
matplotlib.rcParams.update({"font.family":"serif","font.serif":["Times New Roman","Times","Nimbus Roman","STIXGeneral","Liberation Serif","DejaVu Serif"],
 "mathtext.fontset":"stix","font.size":7,"svg.fonttype":"none","savefig.pad_inches":0.02})
K="#000000"; LW=0.6; FS=6.5; MONO=None  # one serif family throughout (report style)
IN="#E6E6E6"; PY="#56B4E9"; SIM="#0072B2"; OUT="#F2DCA0"; ITEM="#FFFFFF"
fig,ax=plt.subplots(figsize=(7.16,8.1))

def box(cx,cy,w,h,title,sub="",fc=IN,tc=K,mono=True,ls="-",z=2,tfs=7.5):
    tfs=7.5
    ax.add_patch(FancyBboxPatch((cx-w/2,-(cy+h/2)),w,h,boxstyle="round,pad=0,rounding_size=22",
        mutation_aspect=1,fc=fc,ec=K,lw=LW,ls=ls,zorder=z))
    fam=MONO if mono else None
    if sub:
        ax.text(cx,-(cy-h/2+26),title,ha="center",va="center",fontsize=tfs,weight="bold",color=tc,family=fam,zorder=z+0.5)
        ax.text(cx,-(cy+18),sub,ha="center",va="center",fontsize=FS,color=tc,zorder=z+0.5,linespacing=1.05)
    else:
        ax.text(cx,-cy,title,ha="center",va="center",fontsize=tfs,weight="bold",color=tc,family=fam,zorder=z+0.5)

def tag(cx,cy,txt="Parameters"):
    ax.add_patch(FancyBboxPatch((cx-85,-(cy+16)),170,32,boxstyle="round,pad=0,rounding_size=14",fc="white",ec=K,lw=0.5,zorder=4))
    ax.text(cx,-cy,txt,ha="center",va="center",fontsize=FS,zorder=5)

def path(pts,ls="-",head=True,rad=0):
    xs=[p[0] for p in pts]; ys=[-p[1] for p in pts]
    if len(pts)>2: ax.plot(xs[:-1],ys[:-1],color=K,lw=0.7,ls=ls,zorder=1,solid_joinstyle="round")
    a,b=(xs[-2],ys[-2]),(xs[-1],ys[-1])
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle="-|>" if head else "-",mutation_scale=7,lw=0.7,color=K,ls=ls,
        connectionstyle=f"arc3,rad={rad}",shrinkA=0,shrinkB=0,zorder=1))

def note(x,y,s,ha="left",rot=0,va="center"):
    ax.text(x,-y,s,ha=ha,va=va,fontsize=FS,rotation=rot,linespacing=1.15,zorder=3)

# --- blocks (poster positions) ---
box(465,130,410,150,"config file","Contains Machine_ID, number of GPUs,\nGPU_IDs, file paths, and\nother simulation settings",mono=False)
box(275,330,330,140,"params.csv","List of set of parameters")
box(650,330,330,150,"Template.mx3","MuMax3 code with placeholder\nvalues to be replaced every\niteration")
box(465,535,330,130,"runner.py",fc=PY)
box(465,750,330,140,"run_{hash}.mx3"); tag(465,822)
box(465,985,330,130,"runner.py",fc=PY)
box(465,1330,410,310,"",fc=SIM,z=1.5); ax.text(465,-1225,"MuMax3",ha="center",va="center",fontsize=7.5,weight="bold",color="white",zorder=3)
box(465,1355,330,140,"run_{hash}.mx3",z=2.5); tag(465,1428)
box(1030,765,330,140,"autoplot.py",fc=PY)
box(960,1195,335,62,"run_{hash}.out folder",fc=OUT,mono=False,tfs=7)
box(1035,1268,330,58,"Magnetization table",fc=ITEM,mono=False,tfs=6.8)
box(1035,1340,330,58,"Other run data",fc=ITEM,mono=False,tfs=6.8)
box(980,1490,330,130,"runner.py",fc=PY)
box(470,1795,345,170,"Terminal","Displays live progress and\nswitching statistics, GPU\nscheduling info, time\nestimates",fc=K,tc="white",mono=False)
box(1065,1615,335,62,"results",fc=OUT,mono=False,tfs=7)
box(1150,1720,380,120,"tables_data","",fc=ITEM)
box(1150,1850,380,120,"metadata","",fc=ITEM)
box(1150,1980,380,120,"plots","",fc=ITEM)
# item descriptions (poster text)
for y,s in [(1720,"magnetization data for every iteration labeled with\niteration number and settings based hash"),
            (1850,"settings for every iteration labeled with iteration\nnumber and settings based hash"),
            (1980,"overlay plot containing all iteration trajectories and\nswitching statistics")]:
    ax.texts[-1]  # keep order
for t in ax.texts[:]:
    if t.get_text() in ("tables_data","metadata","plots"):
        t.set_position((t.get_position()[0],t.get_position()[1]+42)); t.set_fontsize(7.5)
for y,s in [(1720,"magnetization data for every\niteration labeled with iteration\nnumber and settings based hash"),
            (1850,"settings for every iteration\nlabeled with iteration number\nand settings based hash"),
            (1980,"overlay plot containing all\niteration trajectories and\nswitching statistics")]:
    ax.text(1150,-(y+16),s,ha="center",va="center",fontsize=FS,linespacing=1.0,zorder=3)
# tree brackets for folder items
for x0,ys,yt in [(830,[1268,1340],1226),(930,[1720,1850,1980],1646)]:
    path([(x0,yt),(x0,ys[-1])],head=False)
    for y in ys: path([(x0,y),(x0+35 if x0==830 else x0+35,y)],head=False)
# trash icon (delete)
tx,ty=720,1490
ax.add_patch(Rectangle((tx-16,-(ty+24)),32,40,fc="white",ec=K,lw=0.6,zorder=3))
ax.plot([tx-22,tx+22],[-(ty-20),-(ty-20)],color=K,lw=0.8,zorder=3)
ax.plot([tx-6,tx+6],[-(ty-26),-(ty-26)],color=K,lw=0.8,zorder=3)
for dx in (-7,0,7): ax.plot([tx+dx,tx+dx],[-(ty-10),-(ty+18)],color=K,lw=0.5,zorder=3)

# --- arrows (poster routing) ---
path([(465,200),(465,470)],ls=(0,(3,2)))                         # config -> runner
path([(250,410),(300,500)],ls=(0,(3,2)),rad=0.5)                 # params -> runner
path([(670,410),(632,500)],ls=(0,(3,2)),rad=-0.5)                # template -> runner
path([(465,600),(465,680)]); note(492,638,"builds file for 1 iteration")
path([(465,838),(465,920)],ls=(0,(3,2)))
path([(465,1050),(465,1175)]); note(492,1108,"creates job,\nassigns job to GPU,\nruns job with MuMax3")
path([(680,1330),(790,1195)],rad=0.35)                           # MuMax3 -> out folder
path([(1130,1195),(1245,1195),(1245,1490),(1148,1490)])          # out folder -> runner (post)
path([(813,1490),(748,1490)])                                    # runner -> delete
note(835,1620,"reformats run data, labels the data with parameters, saves\nthe reformatted table, creates and saves metadata file,\ncleans up old output folder and .mx3 file, updates statistics\ntrackers and prints to terminal",ha="right")
path([(860,1555),(860,1720),(930,1720)])                         # runner -> tables_data
path([(860,1720),(860,1850),(930,1850)])                         # runner -> metadata
path([(860,1850),(860,1795),(640,1795)])                         # runner -> terminal
path([(300,1795),(90,1795),(90,535),(298,535)])                  # loop to next iteration
note(68,1165,"loops around to next iteration",ha="center",rot=90)
path([(632,530),(1025,530),(1025,693)])                          # runner -> autoplot
note(1040,590,"upon finishing all iterations\nof a parameter set, the\nparameter set values are\npassed to autoplot")
path([(1030,837),(1030,875),(1420,875),(1420,1980),(1342,1980)]) # autoplot -> plots
note(1445,1360,"an overlay plot with statistics table is saved for each parameter set in plots folder",ha="center",rot=-90)
path([(1342,1720),(1385,1720),(1385,1095),(835,1095),(835,567),(642,567)],ls=(0,(3,2)))  # cache check
path([(1342,1850),(1385,1850),(1385,1720)],ls=(0,(3,2)),head=False)
note(852,1020,"checks existing files for matching\nparameter, seed and hash values, then\ncaches and skips current iteration upon\nfinding a match")

ax.set_xlim(40,1475); ax.set_ylim(-2050,-45); ax.axis("off")
import os; os.makedirs("plots",exist_ok=True); o="plots/paper_setup_diagram"
fig.savefig(o+".svg",bbox_inches="tight",facecolor="white"); fig.savefig(o+".png",dpi=300,bbox_inches="tight",facecolor="white")
