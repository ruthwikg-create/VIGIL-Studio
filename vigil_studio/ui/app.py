"""VIGIL Studio native offline desktop user interface (Tk 8.6 / Matplotlib).
Every action is local, explicitly research-only. No network services are started.
"""
from __future__ import annotations
import json,os,sys,tempfile,threading,queue,traceback,datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox,simpledialog
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg,NavigationToolbar2Tk
from .. import __version__
from ..core.store import Workspace
from ..core.demo import make_demo
from ..core.importers import open_record
from ..core.processing import analyze_record,filter_trace,normalized_type,FEATURE_FIELDS
from ..core.reporting import export_window_csv,export_waveform_csv,pdf_report
from ..core.modeling import train_experiment,save_model
from .preferences import (load_preferences, save_preferences, DEFAULT_SIDEBAR_FONT, MIN_SIDEBAR_FONT, MAX_SIDEBAR_FONT)
from .branding import apply_window_icon, sidebar_icon

# Instrument-first laboratory identity: parchment surfaces + dark mineral rail.
# Different from the dark/navy card-dashboard used in VIGIL v3.
C={'bg':'#E9EBE5','sidebar':'#202A2B','surface':'#FAFAF6','surface2':'#E8EDE8',
   'line':'#C5CEC8','white':'#253536','muted':'#637575','accent':'#D36843','blue':'#268D91',
   'warning':'#B87729','danger':'#B74848','chart':'#FCFCF8','side_text':'#E8F0EB',
   'side_muted':'#A9B9B4','side_line':'#3F5150','dark':'#253536',
   'grid_minor':'#E4E9E2','select':'#DCEAE6'}
CH_COLORS={'ECG':'#B75039','PPG':'#178789','ABP':'#5861A4','RESP':'#AC8043',
           'EEG':'#7F5D9C','EMG':'#477F57'}
PAGE_META={
    'Overview':('01','SESSION / WORKBENCH','Workspace'),
    'Signal Lab':('02','ACQUISITION / SIGNAL VIEWER','Workspace'),
    'Quality Explorer':('03','REVIEW / QUALITY TIMELINE','Workspace'),
    'Modality Lab':('04','ANALYSIS / SPECTRAL TOOLS','Workspace'),
    'Annotation Studio':('05','REVIEW / INTERVAL LABELS','Workspace'),
    'AI Experiments':('06','EXPERIMENTS / CLASSICAL ML','Research'),
    'Deep Learning Lab':('07','EXPERIMENTS / PYTORCH','Research'),
    'Foundation Models':('08','MODELS / REPRESENTATIONS','Research'),
    'Research Environment':('09','DATA / OFFICIAL SOURCES','Library'),
    'Reports & Exports':('10','OUTPUT / EVIDENCE','Library'),
    'Audit Trail':('11','GOVERNANCE / LOCAL EVENTS','Library'),
    'Guide & Safety':('12','DOCUMENTATION / LIMITS','Library'),
    'ECG Validation':('13','ECG / REFERENCE BENCHMARK','Research'),
    'Settings':('14','PREFERENCES / ACCESSIBILITY','Workspace')}
# Keep the visible navigation in numerical order, even as new research modules arrive.
NAV_GROUPS=[('WORKSPACE',['Overview','Signal Lab','Quality Explorer','Modality Lab','Annotation Studio']),
            ('MODELS & EXPERIMENTS',['AI Experiments','Deep Learning Lab','Foundation Models']),
            ('DATA & EVIDENCE',['Research Environment','Reports & Exports','Audit Trail','Guide & Safety']),
            ('ECG RESEARCH',['ECG Validation']),
            ('PREFERENCES',['Settings'])]

class Studio(tk.Tk):
    def __init__(self,workspace_path=None):
        super().__init__()
        self.title('VIGIL Studio 4.8  |  Instrument Workbench  |  Developed By Ruthwik Goparaju')
        apply_window_icon(self)
        self.geometry('1510x925');self.minsize(1120,720)
        self.configure(bg=C['bg'])
        self.ws=Workspace(workspace_path)
        self.rec=None;self.analysis=None;self.case_id=None
        self.ecg_eval_result=None;self.ecg_eval_case=None
        self.queue=queue.Queue();self.ai_queue=queue.Queue();self.ai_busy=False;self.busy=False;self.active_page='Overview'
        self.chart_canvas=None;self.chart_figure=None
        self.sidebar_font_size=load_preferences()['sidebar_font_size']
        self._preferences_save_job=None
        self._configure_fonts()
        self._style()
        self._layout()
        self.bind('<Configure>',self._on_window_resize,add='+')
        self.bind('<Control-o>',lambda e:self.import_dialog())
        self.bind('<Control-r>',lambda e:self.refresh_page())
        self.bind('<Control-l>',lambda e:self._case_picker())
        self.bind('<F5>',lambda e:self.refresh_page())
        self.bind('<Control-Right>',lambda e:self._seek_signal(1))
        self.bind('<Control-Left>',lambda e:self._seek_signal(-1))
        for i,name in enumerate(PAGE_META):
            self.bind(f'<Control-{(i+1)%10}>',lambda e,n=name:self.show(n)) if i<9 else None
        self._poll_job=self.after(90,self._poll)
        self.protocol('WM_DELETE_WINDOW',self._close_window)
        self.show('Overview')

    def _configure_fonts(self):
        import tkinter.font as tkfont
        available=set(tkfont.families(self))
        def select(*names):
            return next((n for n in names if n in available),names[-1])
        self.ui_font=select('IBM Plex Sans','Bahnschrift','Aptos','Carlito','DejaVu Sans')
        self.mono_font=select('IBM Plex Mono','Cascadia Mono','Consolas','Cousine','DejaVu Sans Mono')
        self.display_font=select('Bahnschrift','IBM Plex Sans','DejaVu Sans')
        self.option_add('*Font',(self.ui_font,10))

    def _style(self):
        st=ttk.Style(self);st.theme_use('clam')
        st.configure('Dark.Treeview',background=C['surface'],foreground=C['white'],fieldbackground=C['surface'],
            bordercolor=C['line'],rowheight=30,font=(self.mono_font,9),relief='flat')
        st.configure('Dark.Treeview.Heading',background=C['surface2'],foreground=C['dark'],
            bordercolor=C['line'],font=(self.ui_font,9,'bold'),padding=(11,10))
        st.map('Dark.Treeview',background=[('selected',C['select'])],foreground=[('selected',C['dark'])])
        st.configure('Dark.TCombobox',fieldbackground=C['surface'],background=C['surface'],foreground=C['dark'],
            arrowcolor=C['dark'],bordercolor=C['line'],padding=6)
        st.map('Dark.TCombobox',fieldbackground=[('readonly',C['surface'])],foreground=[('readonly',C['dark'])])
        st.configure('Horizontal.TProgressbar',background=C['accent'],troughcolor=C['surface2'])
        st.configure('Instrument.Horizontal.TPanedwindow',background=C['line'],borderwidth=0)
        st.configure('Instrument.Vertical.TPanedwindow',background=C['line'],borderwidth=0)

    def _layout(self):
        self.sidebar=tk.Frame(self,bg=C['sidebar'],width=252,highlightthickness=1,highlightbackground=C['side_line'])
        self.sidebar.pack(side='left',fill='y');self.sidebar.pack_propagate(False)
        branding=tk.Frame(self.sidebar,bg=C['sidebar']);branding.pack(side='top',fill='x',padx=14,pady=(15,10))
        self._sidebar_brand_image=sidebar_icon()
        self.brand_logo=tk.Label(branding,image=self._sidebar_brand_image,bg=C['sidebar'],bd=0,highlightthickness=0)
        self.brand_logo.pack(side='left',padx=(0,4))
        mark=tk.Frame(branding,bg=C['sidebar']);mark.pack(side='left',padx=(3,0))
        self.brand_title=tk.Label(mark,text='VIGIL STUDIO',font=(self.display_font,12,'bold'),fg=C['side_text'],bg=C['sidebar'])
        self.brand_title.pack(anchor='w')
        self.brand_subtitle=tk.Label(mark,text='INSTRUMENT WORKBENCH',font=(self.mono_font,7),fg=C['side_muted'],bg=C['sidebar'])
        self.brand_subtitle.pack(anchor='w')
        tk.Frame(self.sidebar,bg=C['side_line'],height=1).pack(side='top',fill='x',padx=15,pady=(1,7))
        self.sidefoot=tk.Frame(self.sidebar,bg=C['sidebar']);self.sidefoot.pack(side='bottom',fill='x',padx=15,pady=(5,11))
        tk.Frame(self.sidefoot,bg=C['side_line'],height=1).pack(fill='x',pady=(0,8))
        self.foot_session=tk.Label(self.sidefoot,text='●  LOCAL SESSION',font=(self.mono_font,9,'bold'),fg='#7FCDAE',bg=C['sidebar'])
        self.foot_session.pack(anchor='w')
        self.foot_disclaimer=tk.Label(self.sidefoot,text='RESEARCH ONLY / NOT FOR CARE',font=(self.mono_font,7),fg=C['side_muted'],bg=C['sidebar'])
        self.foot_disclaimer.pack(anchor='w',pady=(3,0))
        # Scrollable sidebar: larger navigation text must remain reachable on short displays.
        self.nav_shell=tk.Frame(self.sidebar,bg=C['sidebar']);self.nav_shell.pack(fill='both',expand=True)
        self.nav_canvas=tk.Canvas(self.nav_shell,bd=0,highlightthickness=0,bg=C['sidebar'])
        self.nav_scroll=tk.Scrollbar(self.nav_shell,command=self.nav_canvas.yview,width=9,
                                     bg=C['side_line'],troughcolor=C['sidebar'])
        self.nav_canvas.configure(yscrollcommand=self.nav_scroll.set)
        self.nav_canvas.pack(side='left',fill='both',expand=True)
        self.nav_inner=tk.Frame(self.nav_canvas,bg=C['sidebar'])
        self.nav_window=self.nav_canvas.create_window((0,0),window=self.nav_inner,anchor='nw')
        self.nav_inner.bind('<Configure>',self._refresh_nav_scroll)
        self.nav_canvas.bind('<Configure>',self._nav_canvas_resize)
        self.nav={};self.nav_group_labels=[]
        for group,items in NAV_GROUPS:
            group_title=tk.Label(self.nav_inner,text=group,font=(self.mono_font,8,'bold'),fg=C['side_muted'],bg=C['sidebar'])
            group_title.pack(anchor='w',padx=17,pady=(13,5))
            self.nav_group_labels.append(group_title)
            self._bind_nav_wheel(group_title)
            for label in items:
                code=PAGE_META[label][0]
                outer=tk.Frame(self.nav_inner,bg=C['sidebar'],height=31)
                outer.pack(fill='x',padx=(5,5),pady=1)
                outer.pack_propagate(False)
                pip=tk.Frame(outer,bg=C['sidebar'],width=3);pip.pack(side='left',fill='y')
                b=tk.Button(outer,text=f'{code}   {label}',anchor='w',font=(self.ui_font,9),
                    bg=C['sidebar'],fg=C['side_muted'],bd=0,relief='flat',activebackground=C['side_line'],
                    activeforeground=C['side_text'],padx=9,pady=2,highlightthickness=0,cursor='hand2',
                    command=lambda x=label:self.show(x))
                b.pack(side='left',fill='both',expand=True)
                self.nav[label]=(b,outer,pip)
                self._bind_nav_wheel(outer);self._bind_nav_wheel(b)
        self._bind_nav_wheel(self.nav_canvas);self._bind_nav_wheel(self.nav_inner)
        self._set_sidebar_type_size(self.sidebar_font_size)

        self.container=tk.Frame(self,bg=C['bg']);self.container.pack(side='left',fill='both',expand=True)
        command=tk.Frame(self.container,bg=C['surface'],height=48,highlightthickness=1,highlightbackground=C['line'])
        command.pack(fill='x');command.pack_propagate(False)
        tk.Label(command,text='INSTRUMENTS  /  V4.8',font=(self.mono_font,9,'bold'),fg=C['muted'],bg=C['surface']).pack(side='left',padx=(19,21))
        self.button(command,'+ IMPORT',self.import_dialog,'accent').pack(side='left',pady=8,padx=(0,8))
        self.button(command,'CASE LIBRARY',self._case_picker,'secondary').pack(side='left',pady=8,padx=(0,8))
        self.button(command,'SYNTHETIC TEST',lambda:self.demo('baseline'),'secondary').pack(side='left',pady=8,padx=(0,8))
        self.button(command,'SETTINGS',lambda:self.show('Settings'),'secondary').pack(side='left',pady=8)
        self.case_label=tk.Label(command,text='NO RECORD',font=(self.mono_font,9,'bold'),fg=C['blue'],bg=C['surface'],padx=8,pady=8)
        self.case_label.pack(side='right',padx=(7,14))
        self.offline_tag=tk.Label(command,text='●  OFFLINE',font=(self.mono_font,9,'bold'),fg='#46846D',bg=C['surface'])
        self.offline_tag.pack(side='right',padx=5)

        self.topbar=tk.Frame(self.container,bg=C['bg'],height=86,highlightthickness=0)
        self.topbar.pack(fill='x');self.topbar.pack_propagate(False)
        hdr=tk.Frame(self.topbar,bg=C['bg']);hdr.pack(fill='both',expand=True,padx=(24,20),pady=(14,8))
        left=tk.Frame(hdr,bg=C['bg']);left.pack(side='left',anchor='w')
        self.breadcrumb=tk.Label(left,text='',font=(self.mono_font,9,'bold'),fg=C['accent'],bg=C['bg'])
        self.breadcrumb.pack(anchor='w')
        self.heading=tk.Label(left,text='',font=(self.display_font,20,'bold'),fg=C['dark'],bg=C['bg'])
        self.heading.pack(anchor='w')
        self.topcontext=tk.Label(hdr,text='DATA / TRACE / EVIDENCE',font=(self.mono_font,9),fg=C['muted'],bg=C['bg'])
        self.topcontext.pack(side='right',anchor='s',pady=7)
        footer=tk.Frame(self.container,bg=C['sidebar'],height=28);footer.pack(side='bottom',fill='x');footer.pack_propagate(False)
        self.content=tk.Frame(self.container,bg=C['bg']);self.content.pack(fill='both',expand=True,padx=(23,17),pady=(0,12))
        self.status_var=tk.StringVar(value='READY  /  local research mode  /  never use for patient decisions')
        tk.Label(footer,textvariable=self.status_var,font=(self.mono_font,8),fg=C['side_text'],bg=C['sidebar'],anchor='w').pack(side='left',fill='x',expand=True,padx=16)
        tk.Label(footer,text='Developed By Ruthwik Goparaju',font=(self.ui_font,9,'bold'),fg=C['side_text'],bg=C['sidebar']).pack(side='right',padx=14)

    def _bind_nav_wheel(self,widget):
        widget.bind('<MouseWheel>',lambda event:self._nav_wheel(-int(event.delta/120) or (-1 if event.delta>0 else 1)))
        widget.bind('<Button-4>',lambda event:self._nav_wheel(-1))
        widget.bind('<Button-5>',lambda event:self._nav_wheel(1))

    def _nav_wheel(self,steps):
        if self.nav_scroll.winfo_manager():
            self.nav_canvas.yview_scroll(steps,'units')

    def _nav_canvas_resize(self,event):
        self.nav_canvas.itemconfigure(self.nav_window,width=event.width)
        self.after_idle(self._refresh_nav_scroll)

    def _refresh_nav_scroll(self,event=None):
        """Show a nav scrollbar only if items actually exceed the available height."""
        if not self.nav_inner.winfo_exists() or not self.nav_canvas.winfo_exists():
            return
        self.nav_canvas.configure(scrollregion=self.nav_canvas.bbox('all'))
        content_height=self.nav_inner.winfo_reqheight()
        viewport_height=self.nav_canvas.winfo_height()
        overflow=viewport_height > 1 and content_height > viewport_height+2
        visible=bool(self.nav_scroll.winfo_manager())
        if overflow and not visible:
            self.nav_scroll.pack(side='right',fill='y',before=self.nav_canvas)
        elif not overflow and visible:
            self.nav_scroll.pack_forget()
        if not overflow and viewport_height > 1:
            self.nav_canvas.yview_moveto(0)

    def _ensure_nav_visible(self,page):
        if not self.nav_scroll.winfo_manager() or page not in self.nav:
            return
        _,outer,_=self.nav[page]
        top=self.nav_canvas.canvasy(0)
        bottom=top+self.nav_canvas.winfo_height()
        y=outer.winfo_y()
        h=outer.winfo_height()
        extent=max(1,self.nav_inner.winfo_height())
        if y<top+8:
            self.nav_canvas.yview_moveto(max(0,y-10)/extent)
        elif y+h>bottom-8:
            self.nav_canvas.yview_moveto(min(1,(y+h+10-self.nav_canvas.winfo_height())/extent))

    def _set_sidebar_type_size(self,value):
        """Apply accessible sidebar typography without changing scientific chart scaling."""
        from tkinter import font as tkfont
        size=max(MIN_SIDEBAR_FONT,min(MAX_SIDEBAR_FONT,int(float(value))))
        self.sidebar_font_size=size
        for name,(button,outer,_) in self.nav.items():
            button.configure(font=(self.ui_font,size))
            outer.configure(height=max(32,round(size*2.20+10)))
        for group_title in self.nav_group_labels:
            group_title.configure(font=(self.mono_font,max(9,round(size*.80)),'bold'))
        self.foot_session.configure(font=(self.mono_font,max(9,round(size*.83)),'bold'))
        self.foot_disclaimer.configure(font=(self.mono_font,max(8,round(size*.69))))
        self.brand_title.configure(font=(self.display_font,max(12,round(size*1.10)),'bold'))
        self.brand_subtitle.configure(font=(self.mono_font,max(7,round(size*.66))))
        measure=tkfont.Font(root=self,family=self.ui_font,size=size)
        longest=max(measure.measure(f'{PAGE_META[name][0]}   {name}') for name in self.nav)
        width=max(252,min(425,longest+78))
        self.sidebar.configure(width=width)
        self.nav_canvas.configure(scrollregion=self.nav_canvas.bbox('all'))
        self.after_idle(self._refresh_nav_scroll)
        # Width changes can shrink the desktop toolbar and the three-pane workspace.
        if hasattr(self,'container'):
            self.after_idle(self._adapt_command)
            self.after_idle(self._adapt_overview)
        if hasattr(self,'size_readout') and self.size_readout.winfo_exists():
            self.size_readout.configure(text=f'{size} pt')
        return width

    def _sidebar_font_change(self,value):
        self._set_sidebar_type_size(value)
        if hasattr(self,'save_feedback') and self.save_feedback.winfo_exists():
            self.save_feedback.configure(text='Applying…')
        if self._preferences_save_job is not None:
            self.after_cancel(self._preferences_save_job)
        self._preferences_save_job=self.after(350,self._save_sidebar_preference)

    def _save_sidebar_preference(self):
        self._preferences_save_job=None
        try:
            save_preferences(self.sidebar_font_size)
            if hasattr(self,'save_feedback') and self.save_feedback.winfo_exists():
                self.save_feedback.configure(text='Saved automatically · applies to every section')
            self.status(f'Sidebar font size saved: {self.sidebar_font_size} pt')
        except OSError as exc:
            if hasattr(self,'save_feedback') and self.save_feedback.winfo_exists():
                self.save_feedback.configure(text='Could not save preference')
            self.status(f'Display preference not saved: {exc}')

    def _reset_sidebar_preference(self):
        self.sidebar_scale.set(DEFAULT_SIDEBAR_FONT)
        self._sidebar_font_change(str(DEFAULT_SIDEBAR_FONT))

    def _close_window(self):
        if getattr(self,'_poll_job',None) is not None:
            try:self.after_cancel(self._poll_job)
            except tk.TclError:pass
            self._poll_job=None
        if self._preferences_save_job is not None:
            self.after_cancel(self._preferences_save_job)
            self._save_sidebar_preference()
        self.destroy()

    def _settings_page(self):
        self.section(self.content,'Display & accessibility','Adjust the scientific workstation interface to suit your display and reading comfort.')
        card=self.panel(self.content)
        card.pack(fill='x',padx=1,pady=(4,16))
        self.label(card,'SIDEBAR NAVIGATION',11,C['muted'],True).pack(anchor='w',padx=21,pady=(18,7))
        self.label(card,'Text size',17,C['dark'],True).pack(anchor='w',padx=21)
        self.label(card,'Move the slider: text and sidebar width update immediately, and the choice is saved.',10,C['muted']).pack(anchor='w',padx=21,pady=(4,12))
        slider_line=tk.Frame(card,bg=C['surface']);slider_line.pack(fill='x',padx=20,pady=(0,10))
        self.label(slider_line,'Smaller  9 pt',10,C['muted']).pack(side='left')
        self.size_readout=self.label(slider_line,f'{self.sidebar_font_size} pt',14,C['accent'],True)
        self.size_readout.pack(side='right')
        self.sidebar_scale=tk.Scale(card,from_=MIN_SIDEBAR_FONT,to=MAX_SIDEBAR_FONT,orient='horizontal',
            resolution=1,showvalue=False,length=540,sliderlength=22,troughcolor=C['surface2'],
            bg=C['surface'],fg=C['dark'],highlightthickness=0,activebackground=C['accent'],
            command=self._sidebar_font_change)
        self.sidebar_scale.pack(fill='x',padx=21,pady=(0,3));self.sidebar_scale.set(self.sidebar_font_size)
        line=tk.Frame(card,bg=C['surface']);line.pack(fill='x',padx=21,pady=(5,17))
        self.label(line,'Larger  18 pt  •  The navigation becomes scrollable when necessary.',10,C['muted']).pack(side='left')
        self.button(line,'RESET SIZE',self._reset_sidebar_preference,'secondary').pack(side='right')
        self.save_feedback=self.label(card,'Saved automatically · persists after restart',10,C['blue'])
        self.save_feedback.pack(anchor='w',padx=21,pady=(0,20))
        info=self.panel(self.content)
        info.pack(fill='x',padx=1)
        self.label(info,'WHAT THIS SETTING CHANGES',11,C['muted'],True).pack(anchor='w',padx=21,pady=(18,8))
        wrap=self.label(info,'Navigation item labels, section headings and sidebar footer. Waveform plots, axes and analysis results keep their scientific scales.',11,C['dark'],justify='left')
        wrap.pack(fill='x',anchor='w',padx=21,pady=(0,18))
        self._bind_responsive_wrap(info,wrap,60)

    def _bind_responsive_wrap(self,container,label,inset=40):
        """Always wrap explanatory labels inside the available panel width."""
        def fit(event):
            if label.winfo_exists():
                target=max(145,event.width-inset)
                if int(label.cget('wraplength'))!=target:
                    label.configure(wraplength=target)
        container.bind('<Configure>',fit,add='+')
        self.after_idle(lambda:fit(type('E',(),{'width':container.winfo_width()})()) if container.winfo_exists() and label.winfo_exists() else None)

    def label(self,parent,text,size=11,color=None,bold=False,**kw):
        font=self.display_font if size>=17 else self.ui_font
        return tk.Label(parent,text=text,font=(font,size,'bold' if bold else 'normal'),
            fg=color or C['white'],bg=parent.cget('bg'),**kw)

    def button(self,parent,text,command,kind='accent',**kw):
        accent=kind=='accent'
        bg=C['accent'] if accent else C['surface']
        fg='#FFFFFF' if accent else C['dark']
        return tk.Button(parent,text=text,command=command,fg=fg,bg=bg,activeforeground=fg,
            activebackground=('#B95636' if accent else C['surface2']),relief='flat',bd=0,
            padx=13,pady=6,font=(self.ui_font,9,'bold'),cursor='hand2',
            highlightbackground=(C['accent'] if accent else C['line']),highlightthickness=1,**kw)

    def panel(self,parent=None,padx=19,pady=16,**kw):
        return tk.Frame(parent or self.content,bg=C['surface'],highlightbackground=C['line'],
            highlightthickness=1,**kw)

    def combo(self,parent,values,width=18,default=None):
        c=ttk.Combobox(parent,values=values,width=width,state='readonly',style='Dark.TCombobox')
        if values:c.set(default or values[0])
        return c
    def entry(self,parent,width=16):
        return tk.Entry(parent,width=width,bg=C['surface'],fg=C['dark'],insertbackground=C['dark'],
            relief='flat',highlightcolor=C['blue'],highlightthickness=1,
            highlightbackground=C['line'],font=(self.mono_font,10))

    def section(self,parent,title,subtitle=''):
        self.label(parent,title,17,bold=True).pack(anchor='w',pady=(0,4))
        if subtitle:self.label(parent,subtitle,10,C['muted']).pack(anchor='w',pady=(0,14))
    def _table(self,parent,columns,widths=None,height=9):
        frame=tk.Frame(parent,bg=C['surface'])
        tree=ttk.Treeview(frame,columns=columns,show='headings',style='Dark.Treeview',height=height)
        for i,col in enumerate(columns):tree.heading(col,text=col);tree.column(col,width=(widths[i] if widths else 140),anchor='w',minwidth=65)
        scroll=ttk.Scrollbar(frame,command=tree.yview,orient='vertical');tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y');tree.pack(side='left',fill='both',expand=True)
        return frame,tree
    def status(self,msg):self.status_var.set(msg)
    def _notice(self,title,msg):messagebox.showinfo(title,msg,parent=self)
    def _error(self,exc):
        self.status('Error: '+str(exc));messagebox.showerror('VIGIL Studio',str(exc),parent=self)
    def _poll(self):
        try:
            while True:
                ok,payload=self.queue.get_nowait();self.busy=False
                if ok:
                    rec,analysis=payload
                    try:
                        case_id=self.ws.add_case(rec,analysis)
                        self.rec,self.analysis,self.case_id=rec,analysis,case_id
                        self.ecg_eval_result=None;self.ecg_eval_case=None
                        self.status(f'Imported: {rec.name} | {rec.n:,} samples | local ID {case_id}')
                        self.show('Signal Lab')
                    except Exception as e:self._error(e)
                else:self._error(Exception(payload))
        except queue.Empty:pass
        try:
            while True:
                kind,payload=self.ai_queue.get_nowait()
                if kind=='progress':self.status('Deep learning: '+str(payload))
                elif kind=='ok':
                    self.ai_busy=False;self.status('AI operation complete')
                    self._notice('Research operation completed',str(payload)[:1500])
                    self.show(self.active_page)
                elif kind=='error':
                    self.ai_busy=False;self._error(Exception(payload))
        except queue.Empty:pass
        self._poll_job=self.after(90,self._poll)
    def _ai_run(self,call):
        if self.ai_busy or self.busy:
            return self._notice('Operation in progress','Finish the currently running research task first.')
        self.ai_busy=True;self.status('Running research computation • This can take time for large models')
        def work():
            try:self.ai_queue.put(('ok',call()))
            except Exception as exc:self.ai_queue.put(('error',str(exc)))
        threading.Thread(target=work,daemon=True).start()
    def _analyze_async(self,producer):
        if self.busy:return self._notice('Busy','A dataset is already being processed.')
        self.busy=True;self.status('Importing and analysing in background • please keep this window open')
        def work():
            try:
                rec=producer();analysis=analyze_record(rec)
                self.queue.put((True,(rec,analysis)))
            except Exception as e:self.queue.put((False,str(e)))
        threading.Thread(target=work,daemon=True).start()
    def import_dialog(self):
        path=filedialog.askopenfilename(title='Open a de-identified research waveform',filetypes=[('Supported recordings','*.csv *.hea *.dat *.edf *.bdf *.npz'),('All files','*.*')])
        if not path:return
        fs=None
        if Path(path).suffix.lower()=='.csv':
            answer=simpledialog.askstring('Sampling rate','Sampling frequency in Hz (leave blank if CSV includes time/time_s column):',parent=self)
            if answer is None:return
            if answer.strip():
                try:fs=float(answer)
                except ValueError:return self._error(ValueError('Invalid sampling frequency'))
        self._analyze_async(lambda:open_record(path,fs))
    def demo(self,mode):self._analyze_async(lambda:make_demo(mode))
    def show(self,page):
        if page not in PAGE_META:return
        self.active_page=page
        for name,(button,outer,pip) in self.nav.items():
            selected=name==page
            bg=C['side_line'] if selected else C['sidebar']
            button.configure(bg=bg,fg=C['side_text'] if selected else C['side_muted'])
            outer.configure(bg=bg);pip.configure(bg=C['accent'] if selected else bg)
        self.after_idle(lambda selected=page:self._ensure_nav_visible(selected) if self.active_page==selected else None)
        for child in self.content.winfo_children():child.destroy()
        self.chart_canvas=None;self.chart_figure=None
        code,context,_=PAGE_META[page]
        self.breadcrumb.configure(text='VIGIL  /  '+context)
        self.heading.configure(text=('Acquisition desk' if page=='Overview' else page))
        self.case_label.configure(text=(self.rec.name[:33] if self.rec else 'NO RECORD LOADED'))
        self.topcontext.configure(text=(f'{len(self.rec.channels)} CHANNELS  /  {self.rec.fs:g} Hz  /  {self.rec.duration:.1f}s' if self.rec else 'NO DATA  /  READY TO IMPORT'))
        fn={'Overview':self._overview,'Signal Lab':self._signals,'Quality Explorer':self._quality,
            'Modality Lab':self._modality,'Annotation Studio':self._annotation_studio,'ECG Validation':self._ecg_validation,
            'AI Experiments':self._experiments,'Deep Learning Lab':self._deep_learning_lab,
            'Foundation Models':self._foundation_models,'Research Environment':self._research_environment,
            'Reports & Exports':self._exports,'Audit Trail':self._audit_page,'Guide & Safety':self._guide,
            'Settings':self._settings_page}.get(page)
        if fn:fn()

    def refresh_page(self):self.show(self.active_page)
    def _overview(self):
        cases=self.ws.list_cases()
        cap=tk.Frame(self.content,bg=C['bg']);cap.pack(fill='x',pady=(0,9))
        self.label(cap,'01 / RESEARCH DESK',9,C['muted'],True).pack(side='left')
        self.label(cap,'DRAG PANEL DIVIDERS TO RESIZE',9,C['muted']).pack(side='right')
        splitter=ttk.Panedwindow(self.content,orient='horizontal',style='Instrument.Horizontal.TPanedwindow')
        splitter.pack(fill='both',expand=True)
        left=self.panel(splitter,width=238);center=self.panel(splitter);right=self.panel(splitter,width=242)
        splitter.add(left,weight=0);splitter.add(center,weight=1);splitter.add(right,weight=0)
        self._overview_splitter=splitter
        self._overview_inspector=right
        self._overview_inspector_visible=True
        self.after_idle(self._adapt_overview)

        self._instrument_heading(left,'SOURCE LIBRARY','LOCAL / CASES')
        self.label(left,f'{len(cases)} saved recording(s)',10,C['muted']).pack(anchor='w',padx=14,pady=(0,9))
        # Reserve the action strip BEFORE the expandable table, so buttons never
        # disappear below the window at 720px laptop height.
        def open_selected(e=None):
            selected=tree.selection()
            if selected:self.load_case(selected[0])
        controls=tk.Frame(left,bg=C['surface']);controls.pack(side='bottom',fill='x',padx=12,pady=(8,12))
        self.button(controls,'OPEN CASE',open_selected,'secondary').pack(fill='x',pady=(0,6))
        self.button(controls,'IMPORT FILE',self.import_dialog).pack(fill='x')
        listing=tk.Frame(left,bg=C['surface']);listing.pack(fill='both',expand=True,padx=11)
        tf,tree=self._table(listing,('RECORD / SOURCE',),[175],13)
        tf.pack(fill='both',expand=True)
        tf.bind('<Configure>',lambda e:tree.column('RECORD / SOURCE',width=max(120,e.width-24),stretch=True))
        for case in cases[:500]:
            tree.insert('','end',iid=case['id'],values=(case['name'][:40],))
        tree.bind('<Double-1>',open_selected)

        preview_rec=self.rec if self.rec is not None else make_demo('baseline',seconds=18.)
        is_preview=self.rec is None
        top=tk.Frame(center,bg=C['surface']);top.pack(fill='x',padx=15,pady=(13,4))
        self.label(top,'LIVE TRACE INSPECTOR' if not is_preview else 'TRACE PREVIEW  /  SYNTHETIC',12,C['dark'],True).pack(side='left')
        self.label(top,'NOT CLINICAL DATA' if is_preview else 'SOURCE: '+preview_rec.origin[:29],8,C['warning'] if is_preview else C['blue'],True).pack(side='right')
        survey=self.label(center,'Multi-channel waveform survey  •  Use Signal Lab for filtering, time navigation and interactive inspection.',9,C['muted'],justify='left')
        survey.pack(fill='x',padx=15,pady=(0,4))
        self._bind_responsive_wrap(center,survey,44)
        # Reserve the command strip before the large plot takes flexible space.
        strip=tk.Frame(center,bg=C['surface2']);strip.pack(side='bottom',fill='x',padx=11,pady=(0,11))
        self.label(strip,f'{len(preview_rec.channels)} CH    /    {preview_rec.fs:g} Hz    /    {preview_rec.duration:.1f}s',9,C['dark'],True).pack(side='left',padx=10,pady=10)
        self.button(strip,'OPEN SIGNAL LAB',lambda:self.show('Signal Lab'),'secondary').pack(side='right',padx=7,pady=4)
        plotarea=tk.Frame(center,bg=C['surface']);plotarea.pack(fill='both',expand=True,padx=11,pady=(0,6))
        self._draw_workbench_preview(plotarea,preview_rec)

        self._instrument_heading(right,'EXPERIMENT CONTEXT','INSPECTOR / 01')
        stats=[('RECORD',self.rec.name if self.rec else 'No imported file'),
               ('SAMPLING',f'{preview_rec.fs:g} Hz'),('CHANNELS',str(len(preview_rec.channels))),
               ('DURATION',f'{preview_rec.duration:.2f} s'),
               ('SOURCE','Synthetic / preview' if is_preview else preview_rec.origin[:36]),
               ('STATE','Preview only' if is_preview else 'Analyzed / saved')]
        for key,val in stats:
            tk.Label(right,text=key,font=(self.mono_font,8,'bold'),fg=C['muted'],bg=C['surface']).pack(anchor='w',padx=14,pady=(11,1))
            tk.Label(right,text=val,font=(self.ui_font,10),fg=C['dark'],bg=C['surface'],wraplength=195,justify='left').pack(anchor='w',padx=14)
        tk.Frame(right,bg=C['line'],height=1).pack(fill='x',padx=12,pady=(16,8))
        self.label(right,'QUICK OPERATIONS',9,C['muted'],True).pack(anchor='w',padx=13,pady=(0,6))
        for name,page in [('QUALITY REVIEW','Quality Explorer'),('ANNOTATE','Annotation Studio'),
                          ('MODEL RESEARCH','Deep Learning Lab'),('DATASETS','Research Environment')]:
            self.button(right,name,lambda p=page:self.show(p),'secondary').pack(fill='x',padx=11,pady=3)
        self.label(right,'SCIENTIFIC USE ONLY',9,C['warning'],True).pack(anchor='w',padx=13,pady=(14,2))
        tk.Message(right,text='Exploratory indicators do not establish clinical reliability.',bg=C['surface'],
            fg=C['muted'],font=(self.ui_font,9),width=180).pack(anchor='w',padx=13,pady=(0,12))

    def _on_window_resize(self,event):
        if event.widget is self:
            self.after_idle(self._adapt_command)
            if self.active_page=='Overview':
                if getattr(self,'_overview_resize_job',None) is not None:
                    self.after_cancel(self._overview_resize_job)
                self._overview_resize_job=self.after(90,self._adapt_overview)

    def _adapt_command(self):
        if not hasattr(self,'container') or not self.container.winfo_exists():
            return
        width=self.container.winfo_width()
        # Keep the important action buttons usable at Windows scaling / small widths.
        # Recording name and network state remain available in the page/context bar.
        if width < 1100 and self.offline_tag.winfo_manager():
            self.offline_tag.pack_forget()
        elif width >= 1100 and not self.offline_tag.winfo_manager():
            self.offline_tag.pack(side='right',padx=5)
        if width < 950 and self.case_label.winfo_manager():
            self.case_label.pack_forget()
        elif width >= 950 and not self.case_label.winfo_manager():
            self.case_label.pack(side='right',padx=(7,14))

    def _adapt_overview(self):
        self._overview_resize_job=None
        if self.active_page!='Overview':
            return
        splitter=getattr(self,'_overview_splitter',None)
        inspector=getattr(self,'_overview_inspector',None)
        if splitter is None or inspector is None or not splitter.winfo_exists():
            return
        # Width available after the navigation rail + content margins.
        available=self.winfo_width()-self.sidebar.winfo_width()-45
        show_inspector=available>=930
        if show_inspector!=self._overview_inspector_visible:
            if show_inspector:
                splitter.add(inspector,weight=0)
            else:
                splitter.forget(inspector)
            self._overview_inspector_visible=show_inspector
            self.status('Compact workspace: inspector hidden; open Signal Lab for full details' if not show_inspector else 'Full research workbench')
        if show_inspector:
            self._set_panels(splitter,238,242)
        else:
            self._set_panels(splitter,215,0)

    def _set_panels(self,splitter,left_width,right_width):
        # Panes are native draggable Tk sashes. Set useful starting widths,
        # leaving users free to rearrange them.
        try:
            if splitter.winfo_exists():
                total=splitter.winfo_width()
                if total>left_width+right_width+250:
                    splitter.sashpos(0,left_width)
                    if right_width and len(splitter.panes())>2:
                        splitter.sashpos(1,total-right_width)
        except tk.TclError:
            pass

    def _instrument_heading(self,parent,title,subtitle):
        tag=tk.Frame(parent,bg=C['surface']);tag.pack(fill='x',padx=14,pady=(14,9))
        tk.Label(tag,text=title,font=(self.display_font,12,'bold'),fg=C['dark'],bg=C['surface']).pack(anchor='w')
        tk.Label(tag,text=subtitle,font=(self.mono_font,8),fg=C['accent'],bg=C['surface']).pack(anchor='w',pady=(3,0))
        tk.Frame(parent,bg=C['line'],height=1).pack(fill='x',padx=12,pady=(0,8))

    def _draw_workbench_preview(self,parent,rec):
        fig=Figure(figsize=(7.6,5.8),facecolor=C['surface'],dpi=94)
        selected=list(rec.channels)[:4]
        axs=fig.subplots(len(selected),1,sharex=True)
        axs=np.atleast_1d(axs)
        n=min(rec.n,int(9*rec.fs));step=max(1,int(np.ceil(n/3400)))
        t=np.arange(0,n,step)/rec.fs
        for ax,name in zip(axs,selected):
            y=rec.channels[name][:n:step]
            ax.plot(t,y,lw=1.08,color=self._channel_color(name))
            self._axis_style(ax)
            ax.set_ylabel(name.upper()[:14],fontsize=9,labelpad=11,fontfamily=self.mono_font)
            ax.tick_params(axis='both',labelsize=8)
        axs[-1].set_xlabel('ELAPSED TIME  /  s',fontsize=9,fontfamily=self.mono_font)
        fig.subplots_adjust(left=.13,right=.99,top=.975,bottom=.135,hspace=.18)
        canvas=FigureCanvasTkAgg(fig,master=parent)
        canvas.get_tk_widget().pack(fill='both',expand=True)
        canvas.draw_idle()
        self.chart_canvas=canvas;self.chart_figure=fig
        canvas.mpl_connect('motion_notify_event',self._cursor_event)

    def _channel_color(self,name):
        kind=normalized_type(name)
        return CH_COLORS.get(kind,C['blue'])

    def _cursor_event(self,event):
        if event.inaxes and event.xdata is not None and event.ydata is not None:
            self.status(f'TRACE CURSOR  /  t={event.xdata:.3f} s   /   y={event.ydata:.4g}  /  non-clinical research')

    def load_case(self,id):
        try:
            _,self.rec,self.analysis=self.ws.get_case(id);self.case_id=id
            self.ecg_eval_result=None;self.ecg_eval_case=None
            self.status('Loaded '+self.rec.name);self.show('Signal Lab')
        except Exception as e:self._error(e)
    def _need_record(self):
        if self.rec is None:
            p=self.panel();p.pack(fill='x',pady=15)
            self.label(p,'No waveform loaded',16,bold=True).pack(anchor='w',padx=20,pady=(20,6))
            self.label(p,'Import a de-identified CSV / WFDB / EDF recording or use a labelled synthetic fixture.',10,C['muted']).pack(anchor='w',padx=20)
            self.button(p,'Import waveform',self.import_dialog).pack(anchor='w',padx=20,pady=19)
            return True
        return False
    def _signals(self):
        if self._need_record():return
        util=tk.Frame(self.content,bg=C['bg']);util.pack(fill='x',pady=(0,10))
        self.label(util,'02 / MULTI-CHANNEL VIEWER',9,C['muted'],True).pack(side='left')
        self.button(util,'EXPORT SEGMENT',self._export_waveform,'secondary').pack(side='right')
        shell=ttk.Panedwindow(self.content,orient='horizontal',style='Instrument.Horizontal.TPanedwindow')
        shell.pack(fill='both',expand=True)
        left=self.panel(shell,width=244);middle=self.panel(shell);right=self.panel(shell,width=236)
        shell.add(left,weight=0);shell.add(middle,weight=1);shell.add(right,weight=0)
        self.after_idle(lambda:self._set_panels(shell,244,240))
        self._instrument_heading(left,'CHANNEL STACK','ACQUISITION')
        selector=tk.Frame(left,bg=C['surface']);selector.pack(fill='both',expand=True,padx=12)
        self.ch=self.combo(selector,['All channels',*list(self.rec.channels)],22)
        self.ch.pack(fill='x',pady=(6,14));self.ch.bind('<<ComboboxSelected>>',lambda e:self._render_signal())
        for name,raw in self.rec.channels.items():
            row=tk.Frame(selector,bg=C['surface']);row.pack(fill='x',pady=5)
            tk.Frame(row,bg=self._channel_color(name),width=4,height=30).pack(side='left',padx=(0,9))
            val=tk.Frame(row,bg=C['surface']);val.pack(side='left',fill='x')
            self.label(val,name[:21],10,C['dark'],True).pack(anchor='w')
            self.label(val,f'{normalized_type(name)}  /  {self.rec.fs:g} Hz',8,C['muted']).pack(anchor='w')
        self.label(left,'Use channel selector to isolate a trace.',9,C['muted'],wraplength=190,justify='left').pack(side='bottom',padx=13,pady=15)

        ctrl=tk.Frame(middle,bg=C['surface']);ctrl.pack(fill='x',padx=10,pady=(12,5))
        self.label(ctrl,'FILTER',9,C['muted'],True).pack(side='left',padx=(0,5))
        self.fl=self.combo(ctrl,['raw','ecg','ppg','abp','resp','general'],9);self.fl.pack(side='left',padx=(0,9))
        self.label(ctrl,'START',9,C['muted'],True).pack(side='left',padx=(0,5))
        self.start=self.entry(ctrl,7);self.start.insert(0,'0');self.start.pack(side='left',padx=(0,9))
        self.label(ctrl,'SPAN',9,C['muted'],True).pack(side='left',padx=(0,5))
        self.span=self.entry(ctrl,7);self.span.insert(0,'8');self.span.pack(side='left',padx=(0,9))
        self.button(ctrl,'APPLY',self._render_signal).pack(side='left')
        plot=tk.Frame(middle,bg=C['surface']);plot.pack(fill='both',expand=True,padx=8,pady=(2,9))
        self._render_signal(plot)
        self._instrument_heading(right,'TRACE METADATA','READ ONLY')
        meta=[('NAME',self.rec.name[:42]),('SOURCE',self.rec.origin[:30]),('SAMPLE RATE',f'{self.rec.fs:g} Hz'),
            ('CHANNEL COUNT',str(len(self.rec.channels))),('TOTAL DURATION',f'{self.rec.duration:.1f} s'),
            ('SAMPLE COUNT',f'{self.rec.n:,}'),('PREVIEW','Decimated only')]
        for k,v in meta:
            self.label(right,k,8,C['muted'],True).pack(anchor='w',padx=13,pady=(10,1))
            self.label(right,v,10,C['dark'],wraplength=182,justify='left').pack(anchor='w',padx=13)
        self.label(right,'Ctrl + ← / → navigates the trace.',9,C['muted'],wraplength=190,justify='left').pack(side='bottom',padx=13,pady=16)

    def _seek_signal(self,direction):
        if self.active_page!='Signal Lab' or not hasattr(self,'start') or not hasattr(self,'span') or not self.rec:return
        try:
            span=float(self.span.get());pos=max(0,min(self.rec.duration-span,float(self.start.get())+direction*span*.75))
            self.start.delete(0,'end');self.start.insert(0,f'{pos:.2f}');self._render_signal()
        except (TypeError,ValueError):pass

    def _make_plot(self,parent,height=5.5,axes=1):
        fig=Figure(figsize=(10,height),facecolor=C['surface'],dpi=100)
        canvas=FigureCanvasTkAgg(fig,master=parent);canvas.get_tk_widget().pack(fill='both',expand=True,padx=8,pady=8)
        self.chart_figure=fig;self.chart_canvas=canvas
        return fig,canvas
    def _axis_style(self,ax):
        ax.set_facecolor(C['chart']);ax.tick_params(axis='both',colors=C['muted'],labelsize=8)
        ax.grid(color=C['grid_minor'],linewidth=.7,alpha=.85)
        ax.set_axisbelow(True)
        for sp in ax.spines.values():sp.set_color(C['line'])
        ax.xaxis.label.set_color(C['muted']);ax.yaxis.label.set_color(C['muted'])
        ax.title.set_color(C['dark'])

    def _render_signal(self,figbox=None):
        if self.rec is None:return
        if figbox is None:
            if self.chart_canvas is None:return
            old=self.chart_canvas.get_tk_widget().master
            for child in old.winfo_children():child.destroy()
            figbox=old
        try:
            a=max(0,float(self.start.get()));seconds=float(self.span.get())
            if not 0.2<=seconds<=120:raise ValueError('Displayed span must be 0.2–120 seconds')
            names=list(self.rec.channels) if self.ch.get()=='All channels' else [self.ch.get()]
            mode=self.fl.get();end=min(self.rec.n,int((a+seconds)*self.rec.fs));start=int(a*self.rec.fs)
            if start>=end:raise ValueError('Start time exceeds record duration')
            fig,canvas=self._make_plot(figbox,max(4.5,1.38*len(names)+1.6))
            axs=fig.subplots(len(names),1,sharex=True);axs=np.atleast_1d(axs)
            for ax,name in zip(axs,names):
                x=self.rec.channels[name][start:end]
                # For rendering only, plot no more than about 6k values, while computations use original samples.
                step=max(1,int(np.ceil(len(x)/6000)))
                effective_mode=mode
                try:y=filter_trace(x,self.rec.fs,mode=effective_mode)
                except Exception:y=x
                t=(np.arange(start,end,step)/self.rec.fs)
                ax.plot(t,y[::step],color=self._channel_color(name),linewidth=.93)
                self._axis_style(ax);ax.set_ylabel(name[:17],fontsize=9)
                q=self.analysis['channels'][name]['quality']
                ax.text(.99,.94,f"HEURISTIC INDEX {q['quality_score']:.2f}  /  {normalized_type(name)}",color=C['muted'],
                        fontsize=9,ha='right',va='top',transform=ax.transAxes)
            axs[-1].set_xlabel('Time (seconds)',fontsize=9)
            fig.tight_layout(pad=1.1);canvas.draw_idle()
            canvas.mpl_connect('motion_notify_event',self._cursor_event)
            self.status(f'Displaying {len(names)} channel(s) from {a:g}s to {end/self.rec.fs:.2f}s • preview is decimated')
        except Exception as e:self._error(e)
    def _case_picker(self):
        dialog=tk.Toplevel(self);dialog.title('Local case library');dialog.geometry('820x520');dialog.configure(bg=C['bg']);dialog.transient(self)
        self.label(dialog,'Saved research cases',17,bold=True).pack(anchor='w',padx=20,pady=15)
        tf,tree=self._table(dialog,('Name','Created UTC','Channels','Duration'),[280,190,95,100],12);tf.pack(fill='both',expand=True,padx=19,pady=10)
        for case in self.ws.list_cases():
            m=case['metadata'];tree.insert('','end',iid=case['id'],values=(case['name'],case['created'][:19],len(m['channels']),round(m['duration_s'],2)))
        def open_choice(e=None):
            if tree.selection():
                id=tree.selection()[0];dialog.destroy();self.load_case(id)
        tree.bind('<Double-1>',open_choice);self.button(dialog,'Open selected',open_choice).pack(anchor='e',padx=18,pady=12)
    def _quality(self):
        if self._need_record():return
        row=self.panel(self.content);row.pack(fill='x',pady=(0,12))
        self.label(row,'Windowed exploratory signal-quality indicators',15,bold=True).pack(anchor='w',padx=15,pady=(12,4))
        self.label(row,'Quality index is a heuristic, not a calibrated probability. Review all concerning segments manually.',10,C['muted']).pack(anchor='w',padx=15,pady=(0,12))
        top=tk.Frame(self.content,bg=C['bg']);top.pack(fill='both',expand=True)
        graph=self.panel(top);graph.pack(side='left',fill='both',expand=True,padx=(0,10))
        fig,can=self._make_plot(graph,4)
        ax=fig.add_subplot(111)
        for i,(name,info) in enumerate(self.analysis['channels'].items()):
            windows=info['windows'];times=[w['start_s'] for w in windows];scores=[w['quality_score'] for w in windows]
            if times:ax.plot(times,scores,linewidth=1.7,label=name)
        self._axis_style(ax);ax.set_ylim(-.05,1.05);ax.set_xlabel('Segment start (s)');ax.set_ylabel('Exploratory quality index')
        ax.legend(facecolor=C['surface'],labelcolor=C['white'],fontsize=9,loc='lower left')
        fig.tight_layout();can.draw_idle()
        stats=self.panel(top,width=265);stats.pack(side='right',fill='y');stats.pack_propagate(False)
        self.label(stats,'Channel inspection',14,bold=True).pack(anchor='w',padx=16,pady=(14,12))
        for name,d in self.analysis['channels'].items():
            q=d['quality']
            self.label(stats,name[:26],11,bold=True).pack(anchor='w',padx=16,pady=(7,0))
            self.label(stats,f"Index {q['quality_score']:.3f}    •    Available {q['availability']:.1%}",9,C['accent']).pack(anchor='w',padx=16)
            self.label(stats,', '.join(q['flags'])[:36] or 'No heuristic flags',9,C['muted']).pack(anchor='w',padx=16)
        rev=self.panel(self.content);rev.pack(fill='x',pady=(12,0))
        a=tk.Frame(rev,bg=C['surface']);a.pack(fill='x',padx=16,pady=13)
        self.label(a,'Human review:',11,bold=True).pack(side='left',padx=(0,9))
        self.revlabel=self.combo(a,['needs_review','quality_acceptable','quality_unacceptable','not_assessable'],23);self.revlabel.pack(side='left',padx=(0,11))
        self.reviewer=self.entry(a,13);self.reviewer.insert(0,'researcher');self.reviewer.pack(side='left',padx=(0,9))
        self.note=self.entry(a,39);self.note.pack(side='left',padx=(0,8))
        self.button(a,'Save review',self._save_review).pack(side='left')
        self.label(rev,f"Existing case reviews: {len(self.ws.reviews(self.case_id))}",9,C['muted']).pack(anchor='w',padx=16,pady=(0,12))
    def _save_review(self):
        try:
            self.ws.add_review(self.case_id,self.revlabel.get(),self.note.get().strip(),self.reviewer.get().strip())
            self.status('Human review saved with audit trail');self.show('Quality Explorer')
        except Exception as e:self._error(e)
    def _modality(self):
        if self._need_record():return
        from ..core.modalities import feature_report
        self.section(self.content,'Modality-specific biomedical research','EEG bands, EMG descriptors, ECG interval statistics, PPG/ABP exploratory pulses, respiration spectra.')
        bar=self.panel(self.content);bar.pack(fill='x',pady=(0,12))
        x=tk.Frame(bar,bg=C['surface']);x.pack(anchor='w',padx=14,pady=13)
        self.label(x,'Inspect channel',10,C['muted']).pack(side='left',padx=(0,9))
        ch=self.combo(x,list(self.rec.channels),22);ch.pack(side='left',padx=(0,11))
        self.button(x,'Inspect PSD & modality metrics',lambda:self._draw_modality(ch.get()),'accent').pack(side='left')
        chart=self.panel(self.content);chart.pack(fill='both',expand=True)
        self._modality_plot_parent=chart
        self._draw_modality(list(self.rec.channels)[0])
    def _draw_modality(self,name):
        if not self.rec:return
        from scipy.signal import welch
        from ..core.modalities import feature_report
        if not hasattr(self,'_modality_plot_parent'):return
        box=self._modality_plot_parent
        for child in box.winfo_children():child.destroy()
        self.label(box,f'Power spectral density   /   {name}',14,bold=True).pack(anchor='w',padx=14,pady=(13,6))
        figure,canvas=self._make_plot(box,3.5)
        ax=figure.add_subplot(111)
        x=self.rec.channels[name];fs=self.rec.fs
        z=x[np.isfinite(x)]
        if len(z)>64:
            freqs,p=welch(z-np.median(z),fs=fs,nperseg=min(len(z),4096))
            ax.semilogy(freqs,p+1e-15,color=C['accent'],linewidth=1.4)
            ax.set_xlim(0,min(100,fs/2))
        self._axis_style(ax);ax.set_xlabel('Frequency (Hz)');ax.set_ylabel('Spectral density (arbitrary units²/Hz)')
        figure.tight_layout();canvas.draw_idle()
        info=self.analysis.get('modality_features') or feature_report(self.rec)
        sub=info['channels'].get(name,{})
        summary=json.dumps(sub,indent=2,ensure_ascii=False)
        view=tk.Text(box,height=9,bg=C['surface2'],fg=C['white'],relief='flat',font=(self.mono_font,10),
                     wrap='word',highlightthickness=0,padx=13,pady=10)
        view.pack(fill='x',padx=14,pady=(0,13));view.insert('1.0',summary);view.configure(state='disabled')
    def _import_ecg_reference(self):
        path=filedialog.askopenfilename(title='Select original WFDB header for MIT-BIH research recording',
            filetypes=[('WFDB header','*.hea')])
        if not path:return
        self._analyze_async(lambda:open_record(path))

    def _ecg_validation(self):
        """Independent reference-vs-detector research, not disease classification."""
        from ..core.ecg_validation import reference_beats, annotation_counts
        top=self.panel(self.content);top.pack(fill='x',pady=(0,10))
        self.label(top,'ECG REFERENCE BENCHMARK  /  Independent beat-location comparison',14,bold=True).pack(anchor='w',padx=15,pady=(11,5))
        explanation=self.label(top,'REFERENCE = published .atr symbols. PREDICTIONS = peaks found from ECG samples only. '
            'Never interpret this as diagnostic accuracy or an arrhythmia classifier.',9,C['muted'],justify='left')
        explanation.pack(fill='x',padx=15,pady=(0,8))
        self._bind_responsive_wrap(top,explanation,42)
        self.button(top,'IMPORT ORIGINAL .HEA + .DAT + .ATR',self._import_ecg_reference,'accent').pack(anchor='w',padx=15,pady=(0,12))
        if not self.rec:
            self.label(self.content,'Select the original 100.hea file in your MIT-BIH folder. Leave its .dat and .atr files alongside it.',11,C['muted']).pack(anchor='w',padx=10,pady=20)
            return
        if self.rec.annotation.get('source')!='atr':
            missing=self.label(self.content,'The loaded recording does not include published .atr beat annotations. '
                'CSV conversion keeps the ECG but does not carry .atr markers. Import the original WFDB 100.hea instead.',11,
                C['danger'],justify='left')
            missing.pack(fill='x',padx=10,pady=12)
            self._bind_responsive_wrap(self.content,missing,35)
            return
        try:
            count=annotation_counts(self.rec.annotation,self.rec.n)
            reference_beats(self.rec.annotation,self.rec.n)
        except Exception as exc:
            self.label(self.content,f'Invalid reference annotation: {exc}',11,C['danger']).pack(anchor='w')
            return
        available=[c for c in self.rec.channels if normalized_type(c)=='ECG']
        if not available:
            self.label(self.content,'No ECG leads found in this WFDB recording.',11,C['danger']).pack(anchor='w')
            return
        controls=self.panel(self.content);controls.pack(fill='x',pady=(0,9))
        bar=tk.Frame(controls,bg=C['surface']);bar.pack(fill='x',padx=13,pady=(10,6))
        self.label(bar,'LEAD',9,C['muted'],True).pack(side='left',padx=(0,5))
        self.ecg_lead=self.combo(bar,available,15);self.ecg_lead.pack(side='left',padx=(0,12))
        self.label(bar,'START s',9,C['muted'],True).pack(side='left',padx=(0,5))
        self.ecg_start=self.entry(bar,8);self.ecg_start.insert(0,'600' if self.rec.duration>=610 else '0');self.ecg_start.pack(side='left',padx=(0,12))
        self.label(bar,'SPAN s',9,C['muted'],True).pack(side='left',padx=(0,5))
        self.ecg_span=self.entry(bar,7);self.ecg_span.insert(0,'10');self.ecg_span.pack(side='left',padx=(0,12))
        self.label(bar,'MATCH ±s',9,C['muted'],True).pack(side='left',padx=(0,4))
        self.ecg_tolerance=self.combo(bar,['0.15','0.10','0.20'],6);self.ecg_tolerance.pack(side='left',padx=(0,12))
        self.button(bar,'PLOT MARKERS',self._draw_ecg_overlay,'secondary').pack(side='left',padx=(0,9))
        self.button(bar,'RUN INDEPENDENT PEAK TEST',self._run_ecg_benchmark,'accent').pack(side='left')
        line=tk.Frame(controls,bg=C['surface']);line.pack(fill='x',padx=13,pady=(0,9))
        self.label(line,f"REFERENCE BEATS: {sum(count.values()):,}   /   SYMBOLS: " +
            '  '.join(f'{k}={v}' for k,v in count.items())[:110],9,C['muted']).pack(side='left')
        self.ecg_plot_parent=self.panel(self.content);self.ecg_plot_parent.pack(fill='both',expand=True,pady=(0,9))
        self._draw_ecg_overlay()
        result=self.ecg_eval_result if self.ecg_eval_case==self.case_id else None
        if result:
            summary=self.panel(self.content);summary.pack(fill='x',pady=(0,5))
            m=result['comparison']['metrics'];total=result['reference']['n_beat_annotations']
            line=tk.Frame(summary,bg=C['surface']);line.pack(fill='x',padx=12,pady=(8,4))
            fmt=lambda v: 'N/A' if v is None else f'{v:.3f}'
            self.label(line,f"TP {m['tp']}   FP {m['fp']}   FN {m['fn']}   /   REFERENCE {total}   /   "
                f"SENSITIVITY {fmt(m['sensitivity'])}   PPV {fmt(m['positive_predictive_value'])}   "
                f"F1 {fmt(m['f1'])}   /   MEDIAN ERROR {fmt(m['median_abs_timing_error_ms'])} ms",
                10,C['dark'],True).pack(side='left')
            btn=tk.Frame(summary,bg=C['surface']);btn.pack(fill='x',padx=12,pady=(0,8))
            self.button(btn,'EXPORT AUDITABLE JSON',lambda:self._save_ecg_result('json'),'secondary').pack(side='left',padx=(0,8))
            self.button(btn,'EXPORT TP / FP / FN CSV',lambda:self._save_ecg_result('csv'),'secondary').pack(side='left')
            self.label(btn,'Research agreement only; not arrhythmia classification.',9,C['danger']).pack(side='left',padx=12)
        else:
            self.label(self.content,'Run the independent detector to produce TP, FP, FN, sensitivity, PPV and event-timing errors.',9,C['muted']).pack(anchor='w',padx=10)

    def _draw_ecg_overlay(self):
        from ..core.ecg_validation import reference_beats
        try:
            if not self.rec or not hasattr(self,'ecg_plot_parent'):return
            a=float(self.ecg_start.get());duration=float(self.ecg_span.get())
            if not np.isfinite(a) or not np.isfinite(duration) or a<0 or duration<1 or duration>60:
                raise ValueError('Plot start must be non-negative; span must be 1–60 seconds')
            end=min(self.rec.duration,a+duration)
            if end<=a:raise ValueError('Plot start is outside recording')
            lead=self.ecg_lead.get();fs=self.rec.fs
            for child in self.ecg_plot_parent.winfo_children():child.destroy()
            fig,can=self._make_plot(self.ecg_plot_parent,4.1)
            ax=fig.add_subplot(111);self._axis_style(ax)
            s0=int(a*fs);s1=min(self.rec.n,int(end*fs));y=self.rec.channels[lead][s0:s1]
            stride=max(1,int(np.ceil(len(y)/10000)))
            ax.plot(np.arange(s0,s1,stride)/fs,y[::stride],color=self._channel_color(lead),linewidth=1.03,label='ECG waveform')
            marks=[item for item in reference_beats(self.rec.annotation,self.rec.n) if s0<=item['sample']<s1]
            for n,item in enumerate(marks):
                t=item['sample']/fs
                ax.axvline(t,color=C['blue'],linestyle='--',alpha=.65,linewidth=.9,
                           label='Published .atr reference' if n==0 else None)
                ax.annotate(item['symbol'],(t,.98),xycoords=('data','axes fraction'),fontsize=8,
                    color=C['blue'],ha='center',va='top')
            result=self.ecg_eval_result if self.ecg_eval_case==self.case_id else None
            if result and result['channel']==lead:
                peaks=np.asarray(result['detector']['predicted_samples'],dtype=int)
                peaks=peaks[(peaks>=s0)&(peaks<s1)]
                if len(peaks):
                    ax.scatter(peaks/fs,self.rec.channels[lead][peaks],marker='v',color=C['accent'],s=24,
                        zorder=8,label='Detector predictions (not reference)')
            ax.set_xlabel('Time from recording start (seconds)')
            ax.set_ylabel(f'{lead}  /  raw amplitude')
            ax.set_xlim(a,end)
            ax.legend(fontsize=8,loc='lower left',facecolor=C['surface'])
            fig.tight_layout(pad=1.25);can.draw_idle()
            self.status(f'ECG reference overlay: {len(marks)} published beat markers in {a:g}–{end:g}s')
        except Exception as exc:self._error(exc)

    def _run_ecg_benchmark(self):
        from ..core.ecg_validation import evaluate_ecg_record
        try:
            ch=self.ecg_lead.get();tolerance=float(self.ecg_tolerance.get());rec=self.rec;case_id=self.case_id
            def work():
                result=evaluate_ecg_record(rec,ch,tolerance)
                self.ecg_eval_result=result;self.ecg_eval_case=case_id
                m=result['comparison']['metrics']
                return (f"Independent ECG detector evaluation complete\nTP {m['tp']}   FP {m['fp']}   FN {m['fn']}\n"
                    "The result is agreement with reference beat timing, NOT clinical accuracy or arrhythmia classification.")
            self._ai_run(work)
        except Exception as exc:self._error(exc)

    def _save_ecg_result(self,kind):
        from ..core.ecg_validation import export_evaluation_json,export_evaluation_csv
        result=self.ecg_eval_result if self.ecg_eval_case==self.case_id else None
        if not result:return self._error(ValueError('Run the independent ECG benchmark before exporting'))
        path=self._choose('.'+kind,f'{self.rec.name}_ecg_benchmark.'+kind)
        if not path:return
        try:
            (export_evaluation_json if kind=='json' else export_evaluation_csv)(result,path)
            self.status('Research event-level evaluation saved: '+path)
        except Exception as exc:self._error(exc)

    def _annotation_studio(self):
        if self._need_record():return
        self.section(self.content,'Human annotation studio','Labels must be entered by a qualified research reviewer; no labels are generated by AI.')
        p=self.panel(self.content);p.pack(fill='x',pady=(0,13))
        row=tk.Frame(p,bg=C['surface']);row.pack(fill='x',padx=15,pady=(13,8))
        self.label(row,'Channel',9,C['muted']).pack(side='left',padx=(0,5))
        self.annch=self.combo(row,list(self.rec.channels),12);self.annch.pack(side='left',padx=(0,12))
        self.label(row,'Start s',9,C['muted']).pack(side='left',padx=(0,5))
        self.annstart=self.entry(row,7);self.annstart.insert(0,'0');self.annstart.pack(side='left',padx=(0,12))
        self.label(row,'End s',9,C['muted']).pack(side='left',padx=(0,5))
        self.annend=self.entry(row,7);self.annend.insert(0,str(min(10.,self.rec.duration)));self.annend.pack(side='left',padx=(0,12))
        self.label(row,'Quality label',9,C['muted']).pack(side='left',padx=(0,5))
        self.annlabel=self.combo(row,['uncertain','quality_acceptable','quality_unacceptable'],21)
        self.annlabel.pack(side='left')
        row2=tk.Frame(p,bg=C['surface']);row2.pack(fill='x',padx=15,pady=(0,8))
        self.label(row2,'Anonymous subject group ID',9,C['muted']).pack(side='left',padx=(0,6))
        self.anngroup=self.entry(row2,17);self.anngroup.insert(0,'group_for_subject');self.anngroup.pack(side='left',padx=(0,11))
        self.label(row2,'Reviewer',9,C['muted']).pack(side='left',padx=(0,6))
        self.annreviewer=self.entry(row2,12);self.annreviewer.insert(0,'researcher');self.annreviewer.pack(side='left',padx=(0,11))
        self.label(row2,'Note',9,C['muted']).pack(side='left',padx=(0,6))
        self.annnote=self.entry(row2,24);self.annnote.pack(side='left',padx=(0,11))
        self.button(p,'Save human interval annotation',self._save_annotation).pack(anchor='w',padx=15,pady=(0,14))
        self.label(self.content,'Important: use the SAME group ID for all recordings from one subject to avoid cross-record leakage.',10,C['warning']).pack(anchor='w',pady=(0,12))
        history=self.panel(self.content);history.pack(fill='both',expand=True)
        self.label(history,'Saved interval annotations',14,bold=True).pack(anchor='w',padx=14,pady=(12,8))
        tf,tree=self._table(history,('Channel','Start','End','Human label','Group ID','Reviewer'),[120,95,95,180,190,130],11)
        tf.pack(fill='both',expand=True,padx=14,pady=(0,12))
        for item in self.ws.intervals(self.case_id):
            tree.insert('','end',values=(item['channel'],item['start_s'],item['end_s'],item['label'],item['group_id'],item['reviewer']))
    def _save_annotation(self):
        try:
            self.ws.add_interval(self.case_id,self.annch.get(),float(self.annstart.get()),float(self.annend.get()),
                self.anngroup.get(),self.annlabel.get(),self.annreviewer.get(),self.annnote.get())
            self.status('Expert interval annotation saved with provenance • '+self.case_id)
            self.show('Annotation Studio')
        except Exception as e:self._error(e)
    def _export_labeled_features(self):
        path=self._choose('.csv','vigil_independently_labeled_features.csv')
        if not path:return
        try:
            result=self.ws.export_labeled_features(path)
            self._notice('Research label export',f"Human-labelled windows: {result['labeled_windows']}\nExcluded / incomplete: {result['skipped_windows']}\nDo not train if there are too few independent subject groups.")
        except Exception as e:self._error(e)
    def _experiments(self):
        self.section(self.content,'Reproducible AI quality experiments','Grouped evaluation prevents recording leakage. Requires independently labelled research examples.')
        intro=self.panel(self.content);intro.pack(fill='x',pady=(0,12))
        text=('Input: de-identified labels CSV with one row per independently annotated time window. '
              'Each row requires group_id, label and nine signal-quality feature columns. '
              'Classification is about exploratory signal quality—not medical events. '
              'No trained medical model is bundled or represented as validated.')
        tk.Message(intro,text=text,bg=C['surface'],fg=C['white'],font=(self.ui_font,11),width=960).pack(anchor='w',padx=18,pady=17)
        panel=self.panel(self.content);panel.pack(fill='x',pady=(0,13))
        self.label(panel,'Labelling and model pipeline',14,bold=True).pack(anchor='w',padx=18,pady=(15,11))
        btns=tk.Frame(panel,bg=C['surface']);btns.pack(anchor='w',padx=18,pady=(0,15))
        self.button(btns,'Export unlabeled windows',self._export_labelling_template,'secondary').pack(side='left',padx=(0,9))
        self.button(btns,'Export expert-reviewed labels',self._export_labeled_features,'secondary').pack(side='left',padx=(0,9))
        self.button(btns,'Train & evaluate labels CSV',self._run_training).pack(side='left')
        self.label(panel,'Model: group-separated holdout • standardized logistic regression • abstention band • JSON weights',9,C['muted']).pack(anchor='w',padx=18,pady=(0,13))
        logs=self.panel(self.content);logs.pack(fill='both',expand=True)
        self.label(logs,'Experiment history',14,bold=True).pack(anchor='w',padx=18,pady=(14,10))
        tf,tree=self._table(logs,('UTC','Experiment','Balanced accuracy','ROC-AUC','Groups held out'),[170,270,150,140,150],9)
        tf.pack(fill='both',expand=True,padx=16,pady=(0,14))
        for r in self.ws.list_experiments():
            result=json.loads(r['result_json'])
            tree.insert('','end',values=(r['created'][:19],r['name'],result.get('balanced_accuracy'),result.get('roc_auc'),result.get('n_holdout_groups')))
    def _export_labelling_template(self):
        if self.rec is None or self.analysis is None:
            return self._notice('Load a case','Import a waveform first, then create a label template.')
        path=filedialog.asksaveasfilename(defaultextension='.csv',initialfile='quality_labels_REVIEW_ME.csv',filetypes=[('CSV','*.csv')])
        if not path:return
        import csv
        with open(path,'w',newline='',encoding='utf-8') as f:
            cols=['group_id','label','channel','start_s','end_s',*FEATURE_FIELDS]
            w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
            for ch,info in self.analysis['channels'].items():
                for win in info['windows']:
                    w.writerow({'group_id':self.case_id,'label':'', 'channel':ch,'start_s':win['start_s'],
                                'end_s':win['end_s'],**{x:win[x] for x in FEATURE_FIELDS}})
        self._notice('Label template','Template created. Label each window after independent review and combine several independently reviewed recordings. No labels were fabricated.')
    def _run_training(self):
        filename=filedialog.askopenfilename(filetypes=[('Labelled feature CSV','*.csv')],title='Select independently labelled quality segments')
        if not filename:return
        out=filedialog.asksaveasfilename(initialfile='vigil_quality_model.json',defaultextension='.json',filetypes=[('JSON model','*.json')])
        if not out:return
        try:
            metrics,model=train_experiment(filename)
            save_model(model,out)
            eid=self.ws.add_experiment(Path(filename).name,{'dataset_path_local':Path(filename).name,'seed':42},metrics)
            messagebox.showinfo('Research experiment completed',f"Held-out groups: {metrics['n_holdout_groups']}\nBalanced accuracy: {metrics['balanced_accuracy']}\nROC AUC: {metrics['roc_auc']}\nAbstained: {metrics['abstention_fraction']:.1%}\nNo clinical validity implied.\n\nModel saved to {out}",parent=self)
            self.show('AI Experiments')
        except Exception as e:self._error(e)
    def _deep_learning_lab(self):
        self.section(self.content,'Train a real waveform neural network',
                     'Group-disjoint PyTorch experiments • human signal-quality labels • reproducible evidence')
        info=self.panel(self.content);info.pack(fill='x',pady=(0,12))
        tk.Message(info,text=('This lab trains a 1D convolutional network on approved ECG/EEG/EMG/PPG/ABP/RESP waveforms. '
            'It requires a manifest with human-assigned quality labels (0=unacceptable, 1=acceptable), anonymous recording groups, '
            'channel names, source sampling rates and window offsets. Subject or recording groups never cross train, validation and test splits. '
            'The test set is used only after training, validation selection and score calibration. No diagnosis or clinical use is supported.'),
            bg=C['surface'],fg=C['white'],font=(self.ui_font,11),width=900).pack(padx=17,pady=15,anchor='w')
        pane=self.panel(self.content);pane.pack(fill='x',pady=(0,12))
        self.label(pane,'Step 1  ·  Select a de-identified manifest CSV',13,bold=True).pack(anchor='w',padx=18,pady=(15,8))
        row=tk.Frame(pane,bg=C['surface']);row.pack(fill='x',padx=17,pady=(0,10))
        self.manifest_path=self.entry(row,70);self.manifest_path.pack(side='left',fill='x',expand=True,padx=(0,12))
        self.button(row,'Browse CSV',self._browse_training_manifest,'secondary').pack(side='left')
        self.label(pane,'Step 2  ·  Configure a reproducible experiment',13,bold=True).pack(anchor='w',padx=18,pady=(12,9))
        settings=tk.Frame(pane,bg=C['surface']);settings.pack(anchor='w',padx=18,pady=(0,11))
        self.ai_entries={}
        for key,default in [('Epochs','15'),('Batch size','32'),('Seed','42'),('Network width','24')]:
            frame=tk.Frame(settings,bg=C['surface']);frame.pack(side='left',padx=(0,18))
            self.label(frame,key,9,C['muted']).pack(anchor='w')
            e=self.entry(frame,9);e.insert(0,default);e.pack(pady=(4,0));self.ai_entries[key]=e
        b=tk.Frame(pane,bg=C['surface']);b.pack(anchor='w',padx=18,pady=(9,16))
        self.button(b,'Validate cohort',self._validate_ai_manifest,'secondary').pack(side='left',padx=(0,10))
        self.button(b,'Train • evaluate • save experiment',self._train_ai_manifest).pack(side='left')
        summary=self.panel(self.content);summary.pack(fill='both',expand=True)
        self.label(summary,'Files created for every successful experiment',14,bold=True).pack(anchor='w',padx=18,pady=(14,8))
        tk.Message(summary,bg=C['surface'],fg=C['muted'],font=(self.ui_font,10),width=920,
            text=('model.safetensors (safe tensor weights)  •  model_card.json (provenance & inference contract)  •  '
                  'report.json  •  metrics.csv  •  split_assignments.csv  •  learning_curve.csv  •  results_summary.md\n\n'
                  'Predictions are research quality classifications, not disease diagnoses. '
                  'For strong scientific evidence, validate on an external population and independent source instruments.')).pack(anchor='w',padx=18,pady=(0,14))
        if self.rec:
            self.label(summary,'Loaded waveform: '+self.rec.name,10,C['accent']).pack(anchor='w',padx=18,pady=(0,8))
            self.button(summary,'Run a trained quality model on this waveform',self._infer_ai_wave,'secondary').pack(anchor='w',padx=18,pady=(0,14))

    def _browse_training_manifest(self):
        name=filedialog.askopenfilename(title='Select approved waveform cohort manifest',filetypes=[('CSV manifest','*.csv')])
        if name:self.manifest_path.delete(0,'end');self.manifest_path.insert(0,name)

    def _validate_ai_manifest(self):
        manifest=self.manifest_path.get().strip()
        if not manifest:return self._notice('Required input','Choose a manifest CSV first.')
        def job():
            from ..ai.datasets import load_cohort,split_by_group
            c=load_cohort(manifest);tr,va,te=split_by_group(c.y,c.groups)
            return f"Manifest validated\nWindows: {len(c.y)}\nIndependent groups: {len(set(c.groups))}\nTrain/validation/test: {len(tr)}/{len(va)}/{len(te)}\nGroup overlap: 0\nResearch only."
        self._ai_run(job)

    def _train_ai_manifest(self):
        manifest=self.manifest_path.get().strip()
        if not manifest:return self._notice('Required input','Choose a manifest CSV first.')
        output=filedialog.askdirectory(title='Choose a new EMPTY experiment output directory')
        if not output:return
        try:
            from ..ai.experiment import TrainConfig
            cfg=TrainConfig(epochs=int(self.ai_entries['Epochs'].get()),batch_size=int(self.ai_entries['Batch size'].get()),
                seed=int(self.ai_entries['Seed'].get()),width=int(self.ai_entries['Network width'].get()))
        except Exception as exc:return self._error(exc)
        def job():
            from ..ai.experiment import train_model
            report=train_model(manifest,output,cfg,progress=lambda value:self.ai_queue.put(('progress',f"epoch {value['epoch']}: val balanced accuracy {value['val_balanced_accuracy_at_0_5']:.3f}")))
            result=report['test_metrics']
            return f"Experiment saved to {output}\nHoldout windows: {report['test_windows']}\nHoldout ROC-AUC: {result['roc_auc']}\nBalanced accuracy: {result['balanced_accuracy']:.3f}\nNo clinical validity established."
        self._ai_run(job)

    def _infer_ai_wave(self):
        if not self.rec:return
        model=filedialog.askdirectory(title='Choose a trained VIGIL model directory containing model_card.json')
        if not model:return
        ch=simpledialog.askstring('Waveform channel','Exact channel name:',initialvalue=list(self.rec.channels)[0],parent=self)
        if not ch:return
        def job():
            from ..ai.experiment import predict_waveform_quality
            result=predict_waveform_quality(self.rec,ch,model)
            return json.dumps(result,indent=2)
        self._ai_run(job)

    def _foundation_models(self):
        from ..ai.registry import model_status,MOMENT_ID,MOMENT_BYTES
        status=model_status(self.ws.root)
        self.section(self.content,'Open foundation model workspace',
                     'Real downloadable weights • verified SHA-256 • time-series embeddings')
        top=self.panel(self.content);top.pack(fill='x',pady=(0,12))
        self.label(top,'MOMENT-1-large',19,bold=True).pack(anchor='w',padx=19,pady=(15,4))
        self.label(top,'General time-series foundation model  •  Auton Lab / CMU  •  MIT license',10,C['muted']).pack(anchor='w',padx=19,pady=(0,12))
        row=tk.Frame(top,bg=C['surface']);row.pack(fill='x',padx=19,pady=(0,10))
        self.label(row,'VERIFIED LOCAL WEIGHTS' if status['installed'] else 'NOT INSTALLED / NOT VERIFIED',12,C['accent'] if status['installed'] else C['warning'],bold=True).pack(side='left',padx=(0,16))
        self.label(row,f"Checkpoint: {MOMENT_BYTES/1e9:.2f} GB   |   SHA-256 verification required",10,C['muted']).pack(side='left')
        row2=tk.Frame(top,bg=C['surface']);row2.pack(anchor='w',padx=19,pady=(0,17))
        self.button(row2,'Download verified model (~1.39 GB)',self._download_moment).pack(side='left',padx=(0,9))
        self.button(row2,'Refresh status',self.refresh_page,'secondary').pack(side='left')
        features=self.panel(self.content);features.pack(fill='x',pady=(0,12))
        self.label(features,'Research representation engine',14,bold=True).pack(anchor='w',padx=18,pady=(15,7))
        tk.Message(features,bg=C['surface'],fg=C['muted'],font=(self.ui_font,11),width=920,
            text=('Encode fixed 512-sample normalized waveform windows into research embeddings. '
                  'Use representation vectors for offline similarity/feature research and pre-registered experiments. '
                  'The published general-purpose model is not a medical diagnosis model. The external inference adapter '
                  'still requires validation on a machine with downloaded model weights.')).pack(anchor='w',padx=18,pady=(0,10))
        self.button(features,'Encode loaded waveform and export embeddings',self._foundation_embed,'secondary').pack(anchor='w',padx=18,pady=(0,15))
        if not self.rec:self.label(features,'Load a waveform first to enable encoding.',10,C['warning']).pack(anchor='w',padx=18,pady=(0,14))
        limits=self.panel(self.content);limits.pack(fill='both',expand=True)
        self.label(limits,'Hardware and deployment',14,bold=True).pack(anchor='w',padx=18,pady=(15,8))
        tk.Message(limits,bg=C['surface'],fg=C['muted'],font=(self.ui_font,10),width=920,
            text=('Optional 1.39 GB model weights plus real PyTorch/native scientific dependencies create an installed AI environment in the gigabyte range. '
                  'Python 3.11 is recommended for MOMENT. CPU embedding is supported in the integration design but may be slow. '
                  'GPU training requires a compatible separately installed PyTorch CUDA build. '
                  'Installation downloads are not bundled into the source archive.')).pack(anchor='w',padx=18,pady=(0,16))

    def _download_moment(self):
        yes=messagebox.askyesno('Model download consent',
             'Download approximately 1.39 GB of official MOMENT-1-large weights from Hugging Face?\n\n'
             'You must review and accept the upstream MIT license, have enough free disk space, and use a trusted internet connection. '
             'This model is research-only, not medically validated.\n\nProceed?',parent=self)
        if not yes:return
        self._ai_run(lambda: str(__import__('vigil_studio.ai.registry',fromlist=['install_moment']).install_moment(self.ws.root,True)))

    def _foundation_embed(self):
        if self._need_record():return
        from ..ai.registry import model_status
        if not model_status(self.ws.root)['installed']:
            return self._notice('Model missing','Install and verify the 1.39 GB foundation weights first.')
        channel=simpledialog.askstring('Channel','Exact channel to embed:',initialvalue=list(self.rec.channels)[0],parent=self)
        if not channel:return
        out=filedialog.asksaveasfilename(defaultextension='.npz',initialfile='moment_research_embeddings.npz',filetypes=[('NumPy research embeddings','*.npz')])
        if not out:return
        def job():
            from ..ai.datasets import extract_window
            from ..ai.registry import moment_embeddings,MOMENT_ID,MOMENT_SHA256
            times=np.arange(0,max(0,self.rec.duration-4)+.001,2.)[:50]
            X=np.stack([extract_window(self.rec,channel,float(t)) for t in times])
            E=moment_embeddings(X,self.ws.root)
            np.savez_compressed(out,embeddings=E,start_seconds=times,model_sha256=np.array(MOMENT_SHA256),model_id=np.array(MOMENT_ID),research_only=np.array(True))
            return f"Saved {len(E)} embeddings with {E.shape[1]} features to {out}. No diagnostic interpretation supplied."
        self._ai_run(job)

    def _research_environment(self):
        """Manage real public datasets and local compute without implicit downloads."""
        from ..environment.catalog import SOURCES,preset_summary
        from ..environment.inventory import resource_status
        from ..ai.registry import MOMENT_BYTES
        machine=resource_status(self.ws.root)
        overview=preset_summary('research-multimodal-30gb')
        self.section(self.content,'Research source catalogue',
                     'Version-pinned datasets / explicit consent / storage receipts / model provenance')
        # Laboratory status strip (technical readouts, not marketing/KPI tiles).
        stats=self.panel(self.content);stats.pack(fill='x',pady=(0,12))
        h=tk.Frame(stats,bg=C['surface']);h.pack(fill='x',padx=13,pady=10)
        self.label(h,'ACQUISITION STATUS',9,C['accent'],True).pack(side='left',padx=(0,20))
        for title,val in [('FREE',f"{machine['disk_free_gb']:.1f} GB"),
                          ('DATA PLAN',f"{overview['published_uncompressed_gb_approx']:.1f} GB"),
                          ('CHECKPOINT',f'{MOMENT_BYTES/1e9:.2f} GB'),
                          ('SOURCES',str(len(SOURCES)))]:
            cell=tk.Frame(h,bg=C['surface']);cell.pack(side='left',padx=(0,24))
            self.label(cell,title,8,C['muted'],True).pack(anchor='w')
            self.label(cell,val,12,C['dark'],True).pack(anchor='w',pady=(2,0))
        frame=self.panel(self.content);frame.pack(fill='both',expand=True,pady=(0,12))
        self.label(frame,'Official, version-pinned PhysioNet collections',14,bold=True).pack(anchor='w',padx=16,pady=(12,6))
        tf,tree=self._table(frame,('Dataset','Version','License','Approx. unpacked','Local status'),[260,90,130,145,120],6)
        tf.pack(fill='both',expand=True,padx=16,pady=(2,9))
        for d in SOURCES:
            receipt=self.ws.root/'datasets'/d.key/d.version/'vigil_source_receipt.json'
            tree.insert('','end',iid=d.key,values=(d.name,d.version,d.license,f'{d.unpacked_gb:.2f} GB',
                                                   'Receipt found' if receipt.is_file() else 'Not installed'))
        row=tk.Frame(frame,bg=C['surface']);row.pack(anchor='w',padx=16,pady=(0,14))
        self.label(row,'Selected dataset',9,C['muted']).pack(side='left',padx=(0,8))
        self.env_selection=self.combo(row,[d.key for d in SOURCES],width=19);self.env_selection.pack(side='left',padx=(0,10))
        self.button(row,'Install selected',self._install_env_dataset,'secondary').pack(side='left',padx=(0,8))
        self.button(row,'Index installed',self._index_env_dataset,'secondary').pack(side='left',padx=(0,8))
        self.button(row,'Refresh',self.refresh_page,'secondary').pack(side='left')
        bottom=self.panel(self.content);bottom.pack(fill='x')
        self.label(bottom,'Multimodal research collection (~29 GB of source datasets)',14,bold=True).pack(anchor='w',padx=18,pady=(13,7))
        tk.Message(bottom,bg=C['surface'],fg=C['muted'],font=(self.ui_font,10),width=910,
                   text=('Official public data is downloaded ONLY after explicit consent on your computer. '
                         'Source sizes total about 29 GB unpacked across ECG, EEG, sleep, EMG, PPG and respiration; the optional MOMENT checkpoint adds about 1.39 GB. '
                         'PyTorch and scientific libraries add further gigabytes. Allow substantial temporary disk '
                         'space during installation. Research-only: neither the public data nor pretrained model '
                         'is a validated clinical application.')).pack(anchor='w',padx=18,pady=(0,10))
        buttons=tk.Frame(bottom,bg=C['surface']);buttons.pack(anchor='w',padx=18,pady=(0,15))
        self.button(buttons,'Install all datasets (~29 GB, network)',self._install_env_collection).pack(side='left',padx=(0,10))
        self.button(buttons,'View environment status',self._env_diagnostics,'secondary').pack(side='left')

    def _install_env_dataset(self):
        from ..environment.catalog import BY_KEY
        name=self.env_selection.get();d=BY_KEY[name]
        accepted=messagebox.askyesno('Accept upstream research dataset license',
            f'Dataset: {d.name} v{d.version}\nPublisher: PhysioNet\nLicense: {d.license}\n'
            f'Source: {d.page}\nApprox. unpacked: {d.unpacked_gb:.2f} GB\n\n'
            'Read the license at the source. You must have permission to use these data and protect the resulting files. '
            'This action downloads from PhysioNet over the internet and checks ZIP CRC/path safety, '
            'but does not medically validate the contents.\n\nDo you accept the source license and proceed?',parent=self)
        if not accepted:return
        def job():
            from ..environment.downloads import install_dataset
            latest=[-1]
            def cb(value):
                n=int(value.get('bytes',0)//(128*1024*1024))
                if n!=latest[0]:
                    latest[0]=n;self.ai_queue.put(('progress',f'{name}: {value.get("stage")} {value.get("bytes",0)/1e9:.2f} GB'))
            return str(install_dataset(name,self.ws.root,accept_license=True,progress=cb))
        self._ai_run(job)

    def _install_env_collection(self):
        from ..environment.catalog import SOURCES,preset_summary
        info=preset_summary('research-multimodal-30gb')
        names='\n'.join(f' • {d.name}: {d.license}' for d in SOURCES)
        accepted=messagebox.askyesno('Install official research collection',
            'This will fetch multiple large PUBLIC PhysioNet datasets into your local workspace.\n'
            f'Official unpacked sizes total approximately {info["published_uncompressed_gb_approx"]:.1f} GB.\n\n'
            'The model is a SEPARATE download via Foundation Models. Review each upstream license:\n'
            +names+'\n\nDo you accept these source terms and approve network downloads?',parent=self)
        if not accepted:return
        def job():
            from ..environment.downloads import install_dataset
            result=[]
            for d in SOURCES:
                self.ai_queue.put(('progress','Installing '+d.key))
                def cb(value):
                    if value.get('stage')=='extract':self.ai_queue.put(('progress','Extracting '+d.key))
                result.append(install_dataset(d.key,self.ws.root,accept_license=True,progress=cb))
            return json.dumps(result,indent=2)
        self._ai_run(job)

    def _index_env_dataset(self):
        from ..environment.catalog import BY_KEY
        d=BY_KEY[self.env_selection.get()]
        folder=self.ws.root/'datasets'/d.key/d.version
        if not folder.is_dir():return self._notice('Not installed','Install the selected dataset first.')
        out=self.ws.root/'indexes'/f'{d.key}-{d.version}.jsonl'
        self._ai_run(lambda:str(__import__('vigil_studio.environment.inventory',fromlist=['build_wfdb_index'])
                                 .build_wfdb_index(folder,out)))

    def _env_diagnostics(self):
        def job():
            from ..environment.cli import report_status
            from ..environment.inventory import directory_stats
            info=report_status(self.ws.root)
            # Display exact disk/receipt status, with model validity distinctly stated.
            summary={'machine':info['diagnostics'],'datasets':[
                {'id':entry['dataset'],'receipt':entry['installed_receipt'],
                 'disk_gb':round(entry['disk']['bytes']/1e9,3) if 'disk' in entry else 0}
                for entry in info['datasets']],
                'moment_model':info['foundation_model']['status'],
                'clinical_models_validated':0}
            return json.dumps(summary,indent=2)
        self._ai_run(job)

    def _exports(self):
        """Instrument-style evidence centre with grouped, accessible export actions."""
        if self._need_record():return
        sc=tk.Frame(self.content,bg=C['bg'])
        sc.pack(fill='both',expand=True)
        vertical=tk.Scrollbar(sc,orient='vertical')
        vertical.pack(side='right',fill='y')
        canvas=tk.Canvas(sc,bg=C['bg'],bd=0,highlightthickness=0,yscrollcommand=vertical.set)
        canvas.pack(side='left',fill='both',expand=True)
        vertical.configure(command=canvas.yview)
        body=tk.Frame(canvas,bg=C['bg'])
        viewport=canvas.create_window((0,0),window=body,anchor='nw')
        body.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(viewport,width=e.width))
        def wheel(event):
            if self.active_page=='Reports & Exports':
                canvas.yview_scroll(int(-event.delta/120) if event.delta else 0,'units')
        for target in (canvas,body):target.bind('<MouseWheel>',wheel)

        # Primary publishing console: use the real case, never syntheticized metrics.
        hero=tk.Frame(body,bg=C['sidebar'],highlightbackground=C['side_line'],highlightthickness=1)
        hero.pack(fill='x',pady=(0,13))
        left=tk.Frame(hero,bg=C['sidebar']);left.pack(side='left',fill='both',expand=True,padx=22,pady=18)
        tk.Label(left,text='EVIDENCE STUDIO   /   CONTROLLED RESEARCH EXPORTS',bg=C['sidebar'],
                 fg='#EA986C',font=(self.mono_font,9,'bold')).pack(anchor='w')
        tk.Label(left,text='Scientific reporting workspace',bg=C['sidebar'],fg='#F5F6F2',
                 font=(self.display_font,20,'bold')).pack(anchor='w',pady=(6,6))
        tk.Label(left,text='Publication-style PDF • traceable datasets • reproducible evidence bundle',
                 bg=C['sidebar'],fg=C['side_muted'],font=(self.ui_font,10),anchor='w',
                 justify='left',wraplength=650).pack(anchor='w')
        hero_buttons=tk.Frame(hero,bg=C['sidebar']);hero_buttons.pack(side='right',padx=19,pady=14)
        self.button(hero_buttons,'GENERATE PDF DOSSIER',self._pdf,'accent').pack(fill='x',pady=(0,6))
        self.button(hero_buttons,'EXPORT EVIDENCE PACKAGE',self._evidence_package,'secondary').pack(fill='x')
        self.button(hero_buttons,'VERIFY EXPORTED ZIP',self._verify_evidence_package,'secondary').pack(fill='x',pady=(6,0))

        # Provenance strip ties visual output to the actual imported record.
        strip=tk.Frame(body,bg=C['surface'],highlightbackground=C['line'],highlightthickness=1)
        strip.pack(fill='x',pady=(0,15))
        for i,(k,v) in enumerate((('ACTIVE RECORD',self.rec.name),
                                  ('SOURCE',self.rec.origin),
                                  ('CHANNELS',str(len(self.rec.channels))),
                                  ('ACQUISITION',f'{self.rec.fs:g} Hz  /  {self.rec.duration:.1f} s'))):
            cell=tk.Frame(strip,bg=C['surface']);cell.pack(side='left',fill='both',expand=True,padx=14,pady=11)
            self.label(cell,k,8,C['muted'],True).pack(anchor='w')
            self.label(cell,str(v)[:44],10,C['dark'],True,wraplength=265,justify='left').pack(anchor='w',pady=(3,0))
            if i<3:tk.Frame(strip,width=1,bg=C['line']).pack(side='left',fill='y',pady=8)

        self.label(body,'OUTPUT PRODUCTS',11,C['dark'],True).pack(anchor='w',pady=(1,7))
        self.label(body,'Choose a report for people or an unchanged data format for analysis software.',
                   9,C['muted']).pack(anchor='w',pady=(0,10))
        columns=tk.Frame(body,bg=C['bg']);columns.pack(fill='x')
        columns.columnconfigure(0,weight=1,uniform='cols')
        columns.columnconfigure(1,weight=1,uniform='cols')
        doc=tk.Frame(columns,bg=C['surface'],highlightbackground=C['line'],highlightthickness=1)
        data=tk.Frame(columns,bg=C['surface'],highlightbackground=C['line'],highlightthickness=1)
        doc.grid(row=0,column=0,sticky='nsew',padx=(0,7))
        data.grid(row=0,column=1,sticky='nsew',padx=(7,0))
        # On laptop-width content areas, arrange each evidence product category
        # in a full-width row so labels and export controls cannot overlap.
        self._export_columns_compact=None
        def responsive_exports(event):
            compact=event.width<920
            if compact==self._export_columns_compact:return
            self._export_columns_compact=compact
            if compact:
                columns.columnconfigure(0,weight=1,uniform='')
                columns.columnconfigure(1,weight=0,uniform='')
                doc.grid_configure(row=0,column=0,padx=0,pady=(0,12))
                data.grid_configure(row=1,column=0,padx=0,pady=0)
            else:
                columns.columnconfigure(0,weight=1,uniform='cols')
                columns.columnconfigure(1,weight=1,uniform='cols')
                doc.grid_configure(row=0,column=0,padx=(0,7),pady=0)
                data.grid_configure(row=0,column=1,padx=(7,0),pady=0)
        columns.bind('<Configure>',responsive_exports,add='+')
        self._export_group_title(doc,'01   SCIENTIFIC DOCUMENTS','Designed for researchers, reviewers and project supervisors.')
        self._export_group_title(data,'02   ANALYSIS DATA','Schema-preserving outputs for Python, MATLAB and statistics.')
        self._export_action(doc,'Full research PDF dossier',
            'Four structured sections: evidence summary, signals, quality trends, review and limitations.',
            'GENERATE PDF',self._pdf,featured=True)
        self._export_action(doc,'Complete evidence package',
            'Branded PDF + offline HTML index + case metadata + window CSV + data dictionary + SHA-256 manifest.',
            'BUILD PACKAGE',self._evidence_package)
        self._export_action(doc,'Engineering readiness assessment',
            'Local integrity findings and open clinical release gates, with status clearly differentiated.',
            'EXPORT PDF',self._readiness_pdf)
        self._export_action(data,'Case metadata  /  JSON',
            'Analysis provenance, reviews and descriptions. Raw signal arrays are not embedded.',
            'EXPORT JSON',self._json)
        self._export_action(data,'Time-window features  /  CSV',
            'Every measured window and algorithm flag, with unchanged numeric columns.',
            'EXPORT CSV',self._window_csv)
        self._export_action(data,'Expert-labelled research dataset',
            'Export records with appropriate independently reviewed labels; review access before sharing.',
            'EXPORT DATA',self._export_labeled_features)

        sharing=tk.Frame(body,bg=C['surface'],highlightbackground=C['line'],highlightthickness=1)
        sharing.pack(fill='x',pady=(14,0))
        self._export_group_title(sharing,'03   CONTROLLED DATA SHARING',
            'Raw waveforms are sensitive research assets. These exports request confirmation.')
        share_row=tk.Frame(sharing,bg=C['surface']);share_row.pack(fill='x',padx=16,pady=(0,12))
        for name,desc,command in [
            ('Waveform segment CSV','Short selected waveform excerpt',self._export_waveform),
            ('Raw research case bundle','Unencrypted NPZ waveform + JSON',self._bundle)]:
            tile=tk.Frame(share_row,bg=C['surface2']);tile.pack(side='left',fill='both',expand=True,padx=(0,8))
            self.label(tile,name,11,C['dark'],True).pack(anchor='w',padx=12,pady=(10,2))
            self.label(tile,desc,9,C['muted']).pack(anchor='w',padx=12)
            self.button(tile,'EXPORT',command,'secondary').pack(anchor='w',padx=12,pady=(8,10))

        footer=tk.Frame(body,bg=C['bg']);footer.pack(fill='x',pady=(10,8))
        tk.Frame(footer,bg=C['accent'],width=3).pack(side='left',fill='y',padx=(0,9))
        self.label(footer,'RESEARCH USE ONLY  /  Data exports must be checked for consent, provenance and de-identification. '
                   'A professional PDF does not establish clinical clearance.',9,C['muted'],wraplength=950,justify='left').pack(side='left')

    def _export_group_title(self,parent,title,subtitle):
        top=tk.Frame(parent,bg=C['surface']);top.pack(fill='x',padx=16,pady=(12,7))
        self.label(top,title,10,C['accent'],True).pack(anchor='w')
        self.label(top,subtitle,9,C['muted'],wraplength=500,justify='left').pack(anchor='w',pady=(3,0))
        tk.Frame(parent,bg=C['line'],height=1).pack(fill='x',padx=16,pady=(0,4))

    def _export_action(self,parent,name,description,button,command,featured=False):
        line=tk.Frame(parent,bg=C['surface']);line.pack(fill='x',padx=15,pady=(7,8))
        tk.Frame(line,bg=C['accent'] if featured else C['blue'],width=3).pack(side='left',fill='y',padx=(0,11))
        right=tk.Frame(line,bg=C['surface']);right.pack(side='right',padx=(7,0))
        self.button(right,button,command,'accent' if featured else 'secondary').pack(pady=9)
        txt=tk.Frame(line,bg=C['surface']);txt.pack(side='left',fill='both',expand=True,pady=2)
        self.label(txt,name,11,C['dark'],True).pack(anchor='w')
        self.label(txt,description,9,C['muted'],wraplength=430,justify='left').pack(anchor='w',pady=(3,0))
        tk.Frame(parent,bg=C['line'],height=1).pack(fill='x',padx=17)

    def _readiness_pdf(self):
        path=self._choose('.pdf','VIGIL_Engineering_Readiness_Assessment.pdf')
        if not path:return
        try:
            from ..safety.gates import assess_release
            from ..core.professional_reports import write_readiness_pdf
            assessment=assess_release(self.ws)
            write_readiness_pdf(assessment,path)
            self.status('Engineering assessment PDF saved: '+str(path))
            messagebox.showinfo('Engineering assessment generated',
                 'Your PDF separates local verification results from clinical release requirements. '
                 'It does not authorize patient care or claim hospital accreditation.',parent=self)
        except Exception as exc:self._error(exc)

    def _verify_evidence_package(self):
        from ..core.evidence_bundle import verify_evidence_package
        file_path=filedialog.askopenfilename(title='Select a VIGIL evidence package',
                              filetypes=[('Research evidence ZIP','*.zip')],parent=self)
        if not file_path:return
        try:
            result=verify_evidence_package(file_path)
            self.status('Evidence file consistency verified: '+str(file_path))
            messagebox.showinfo('Evidence integrity verification',
                f"PASS: {result['files_checked']} evidence files match the recorded manifest.\n"
                f"Record: {result['record_name']}\n\n"
                'This verifies file consistency only, not medical correctness, independent signing, '
                'hospital authorization or clinical validity.',parent=self)
        except Exception as exc:self._error(exc)

    def _evidence_package(self):
        if not self.rec:return
        if not messagebox.askyesno('Controlled evidence package',
             'This ZIP includes a PDF, metadata, time-window measurements, human-review records, '
             'a data dictionary and a source hash manifest.\n\n'
             'It does NOT include raw waveform arrays, but reviewer notes and metadata may contain sensitive '
             'information. Confirm the record has been de-identified and the recipient is authorized. Continue?',parent=self):return
        path=self._choose('.zip','VIGIL_Research_Evidence_Package.zip')
        if not path:return
        try:
            from ..core.evidence_bundle import export_evidence_package
            export_evidence_package(self.ws,self.case_id,self.rec,self.analysis,path)
            self.status('Evidence package saved: '+str(path))
            messagebox.showinfo('Evidence package generated',
               'The package contains a professional PDF, offline HTML index, quality CSV, case JSON, '
               'data dictionary and SHA-256 manifest.\n\nResearch use only. No clinical clearance is implied.',parent=self)
        except Exception as exc:self._error(exc)
    def _choose(self,ext,name):return filedialog.asksaveasfilename(defaultextension=ext,initialfile=name,filetypes=[(ext.upper(),'*'+ext)])
    def _pdf(self):
        if self.rec is None:return
        path=self._choose('.pdf','VIGIL_Professional_Research_Dossier.pdf')
        if not path:return
        try:
            pdf_report(self.rec,self.analysis,self.ws.reviews(self.case_id),path)
            self.status('Professional research PDF saved: '+path)
        except Exception as exc:self._error(exc)
    def _json(self):
        path=self._choose('.json','vigil_case.json')
        if path:
            try:self.ws.export_case_json(self.case_id,path);self.status('JSON exported: '+path)
            except Exception as e:self._error(e)
    def _window_csv(self):
        path=self._choose('.csv','vigil_quality_windows.csv')
        if path:
            try:export_window_csv(self.analysis,path);self.status('Window features exported: '+path)
            except Exception as e:self._error(e)
    def _export_waveform(self):
        if not self.rec:return
        if not messagebox.askyesno('Unencrypted research export',
            'This action writes RAW waveform data as an UNENCRYPTED CSV file. '
            'Only export properly de-identified research data to an approved location. '
            'This is not a hospital patient-data export. Continue?',parent=self):return
        t=simpledialog.askfloat('Segment start','Starting time (s)',initialvalue=0,minvalue=0,parent=self)
        if t is None:return
        d=simpledialog.askfloat('Segment duration','Duration (seconds, max 120)',initialvalue=10,minvalue=.1,maxvalue=120,parent=self)
        if d is None:return
        path=self._choose('.csv','vigil_waveform_segment.csv')
        if path:
            try:export_waveform_csv(self.rec,path,t,d);self.status('Waveform segment exported: '+path)
            except Exception as e:self._error(e)
    def _bundle(self):
        if not messagebox.askyesno('Unencrypted research bundle',
            'The ZIP will contain RAW waveform arrays and potentially sensitive '
            'research metadata. The ZIP is NOT encrypted. Use only de-identified '
            'research records and approved storage. Continue?',parent=self):return
        path=self._choose('.zip','vigil_case_bundle.zip')
        if not path:return
        import zipfile
        try:
            with tempfile.TemporaryDirectory() as temp:
                report=Path(temp)/'analysis.json';self.ws.export_case_json(self.case_id,report)
                raw=self.ws.records/(self.case_id+'.npz')
                with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
                    z.write(report,'analysis.json');z.write(raw,'recording.npz')
                    z.writestr('READ_FIRST.txt','Research-only data. Check consent and authorized data sharing. No clinical use.\n')
            self.status('Research bundle saved: '+path)
        except Exception as e:self._error(e)
    def _audit_page(self):
        status=self.ws.verify_audit()
        p=self.panel(self.content);p.pack(fill='x',pady=(0,14))
        self.label(p,'Local audit chain: '+('VERIFIED' if status['valid'] else 'FAILED'),17,C['accent'] if status['valid'] else C['danger'],bold=True).pack(anchor='w',padx=18,pady=(13,5))
        self.label(p,f"Events checked: {status['events_checked']}   |   SHA-256 chained log (NOT tamper-proof)",10,C['muted']).pack(anchor='w',padx=18,pady=(0,13))
        panel=self.panel(self.content);panel.pack(fill='both',expand=True)
        tf,tree=self._table(panel,('Seq','UTC','Event','Subject','Hash prefix'),[65,190,175,240,220],17)
        tf.pack(fill='both',expand=True,padx=14,pady=14)
        for r in reversed(self.ws.audit()):tree.insert('','end',values=(r['seq'],r['utc'][:19],r['kind'],r['subject'],r['hash'][:24]))
    def _run_local_safety_check(self):
        """Informational checks only: no permission to use VIGIL for patient care."""
        from ..safety.gates import assess_release
        try:
            report=assess_release(self.ws)
            checks=report['engineering_checks']
            a=checks.get('audit',{})
            r=checks.get('case_files',{})
            messagebox.showwarning('Hospital readiness — clinical use BLOCKED',
                'CLINICAL RELEASE: BLOCKED\n\n'
                f"Local audit: {'PASS' if a.get('valid') else 'REVIEW NEEDED'}\n"
                f"Waveforms verified: {r.get('verified',0)}\n"
                f"Legacy without digest: {r.get('unverified_legacy',0)}\n"
                f"Integrity failures: {r.get('failed',0)}\n\n"
                'Local checks do NOT establish clinical safety, authorization, or cybersecurity.',parent=self)
        except Exception as e:self._error(e)

    def _research_security_instructions(self):
        messagebox.showinfo('Optional research safeguards — not a clinical security system',
            'Optional security features are available as CLI tools:\n\n'
            '• AES-256-GCM encrypted export of a de-identified research case.\n'
            '• External HMAC seal of the local audit history.\n\n'
            'Install: python -m pip install -r requirements-security.txt\n'
            'Run: python scripts/research_safety_tools.py --help\n\n'
            'CAUTION: The existing research.sqlite3 and records directory remain unencrypted. '
            'Staff accounts, hospital SSO, role-based access, secure key management, '
            'and independent cybersecurity testing are not implemented.\n\n'
            'Do not place identifiable patient data in this workstation.',parent=self)

    def _guide(self):
        self.section(self.content,'Read before using this software','The package is for non-clinical scientific research and education only.')
        gate=self.panel(self.content);gate.pack(fill='x',pady=(0,10))
        self.label(gate,'Clinical deployment status: BLOCKED',14,C['danger'],bold=True).pack(anchor='w',padx=16,pady=(10,4))
        row=tk.Frame(gate,bg=C['surface']);row.pack(anchor='w',padx=16,pady=(0,10))
        self.button(row,'RUN LOCAL INTEGRITY CHECK',self._run_local_safety_check,'secondary').pack(side='left',padx=(0,8))
        self.button(row,'RESEARCH ENCRYPTION & AUDIT',self._research_security_instructions,'secondary').pack(side='left')
        content=[
            ('What it does','Opens ECG/PPG/ABP/respiration and other time-series; explores and annotates signals; runs grouped classical and neural waveform quality experiments; optionally encodes research embeddings with real downloaded foundation weights.'),
            ('What it does NOT do','It does not diagnose a disease, validate a medical device, control an alarm, connect live bedside equipment or make a clinical decision. No hospital deployment or trial clearance is claimed.'),
            ('Data privacy','Workspaces are stored locally, including ORIGINAL RAW waveform samples inside NPZ containers. Do not import identifiable patient data. Keep the workspace on an appropriately secured encrypted system.'),
            ('Actual datasets','For reproducible external evaluation, download a permitted PhysioNet WFDB database using the optional dataset script, verify permissions and labels, and import local records.'),
            ('Study design','Pre-register a hypothesis, de-duplicate by patient/recording, use held-out external datasets, calculate confidence intervals, and have clinicians independently annotate failures.'),
            ('Security','Optional AES-GCM case exports and external audit HMAC seals are available as research safeguards. The original workspace is still unencrypted; no clinical authentication, staff roles, independent cybersecurity attestation or validated QMS exists.'),
            ('Shortcuts','Ctrl+O imports a recording. Ctrl+R refreshes current view. Double-click saved cases to reopen.')]
        for title,desc in content:
            p=self.panel(self.content);p.pack(fill='x',pady=(0,8))
            self.label(p,title,12,bold=True).pack(anchor='w',padx=16,pady=(10,3))
            tk.Message(p,text=desc,bg=C['surface'],fg=C['muted'],font=(self.ui_font,10),width=930).pack(anchor='w',padx=16,pady=(0,12))

def launch(workspace=None):
    app=Studio(workspace);app.mainloop()
