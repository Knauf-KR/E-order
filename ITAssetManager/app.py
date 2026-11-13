"""Knauf IT Asset Manager — local Excel desktop application."""
import os, json, csv, traceback, threading, queue
from collections import Counter
from pathlib import Path
from datetime import date, datetime
from copy import deepcopy
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font
from storage import Store, as_date, display, add_months, ERRORS, digest
from sync_policy import SyncPolicy
from brand import LOGO_PNG

BASE = Path(__file__).resolve().parent
CONFIG = Path(os.environ.get('LOCALAPPDATA',Path.home())) / 'ITAssetManager' / 'settings.json'
NAVY='#003778'; BLUE='#0099DE'; BG='#F3F6F9'; WHITE='#FFFFFF'; INK='#17324D'; MUTED='#6B7D8E'; LINE='#DFE7ED'
ORANGE='#F06E00'; RED='#B83C38'; GREEN='#287A56'
PAGES = {
 'overview':('자산 현황','전체 자산을 살펴보고 필요한 업무로 바로 이동하세요.',None),
 'office':('사무직 자산','개인에게 지급된 사무용 PC와 사용자를 관리합니다.','사무직 List'),
 'shared':('공용 PC','공용 장비의 위치와 사용 목적을 확인합니다.','공용 PC'),
 'desktop':('Plant 데스크탑','현장 데스크탑의 상세 위치와 사용자를 관리합니다.','Plant Desktop'),
 'stock':('창고 자산','보관 중인 자산과 재지급 가능한 장비를 확인합니다.','창고(SAP자산)'),
 'retired':('폐기완료','폐기 처리된 자산을 보관하고 이력을 조회합니다.','폐기완료'),
 'expiry':('교체 · 만료 관리','만료된 자산과 90일 이내 교체 예정 자산을 확인합니다.',None),
 'quality':('데이터 점검','중복 S/N, 누락된 정보와 날짜 오류를 확인합니다.',None),
}

def location_key(value):
    raw=display(value).strip()
    aliases={'dan':'당진','dangjin':'당진','당진':'당진','uls':'울산','ulsan':'울산','울산':'울산','yeo':'여수','yeosu':'여수','여수':'여수','seoul':'서울','서울':'서울'}
    return aliases.get(raw.casefold(),raw or '미등록')

def user_name(item):
    v=item['values']
    return v.get(10) or v.get(12) if item['sheet']=='Plant Desktop' else v.get(9) or v.get(12)

def checks(store,items):
    counts=Counter(display(i['values'].get(5)).strip().casefold() for i in items if i['values'].get(5))
    result={}
    for item in items:
        v=item['values']; notes=[]; sn=display(v.get(5)).strip()
        if not sn: notes.append('S/N 누락')
        elif counts[sn.casefold()]>1: notes.append('S/N 중복')
        if not v.get(7): notes.append('모델 누락')
        if item['sheet']!='폐기완료':
            if not v.get(8): notes.append('위치 누락')
            if not store.expiry(item): notes.append('만료일 확인')
            if item['sheet']=='사무직 List' and not user_name(item): notes.append('사용자 누락')
        if any(isinstance(x,str) and x in ERRORS for x in v.values()): notes.append('엑셀 수식 오류')
        start,end=as_date(v.get(14)),store.expiry(item)
        if start and end and end<start: notes.append('날짜 순서 오류')
        result[(item['sheet'],item['row'])]=notes
    return result

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Knauf | IT 자산 관리 v0.3'); self.geometry(f'{min(1500,max(1120,self.winfo_screenwidth()-60))}x{min(920,max(680,self.winfo_screenheight()-80))}'); self.minsize(1120,680); self.configure(bg=BG)
        families=set(font.families(self))
        self.ui_font=next((f for f in ['맑은 고딕','Malgun Gothic','Noto Sans CJK KR','Arial'] if f in families),'TkDefaultFont')
        self.option_add('*Font',(self.ui_font,10))
        self.store=None; self.items={}; self.page='overview'; self.current_rows=[]; self.selected_item=None; self.sort_col=None; self.reverse=False
        self.dialog=None; self.sap_window=None; self.loaded_at='';
        self._events=queue.Queue();self._sync_policy=SyncPolicy();self._watch_inflight=False;self._watch_loading=False;self.external_changed=False;self._auto_job=None;self._auto_failed=False
        self.auto_save=tk.BooleanVar(value=True)
        try:self.auto_save.set(json.loads(CONFIG.read_text(encoding='utf-8')).get('auto_save',True))
        except Exception:pass
        self.query=tk.StringVar(); self.state=tk.StringVar(value='전체'); self.location=tk.StringVar(value='전체 위치'); self.kind=tk.StringVar(value='전체 종류')
        self._suspend=False; self._search_job=None
        self.styles()
        self.build()
        self.protocol('WM_DELETE_WINDOW',self.close)
        self.bind('<Control-s>',lambda e:self.save()); self.bind('<Control-f>',lambda e:self.search.focus_set()); self.bind('<F5>',lambda e:self.reload())
        self.after(100,self.start)
        self.after(1000,self.monitor_tick);self.after(200,self.monitor_receive)

    def styles(self):
        s=ttk.Style(self); s.theme_use('clam')
        s.configure('.',font=(self.ui_font,10),background=BG,foreground=INK)
        s.configure('TFrame',background=BG); s.configure('White.TFrame',background=WHITE)
        s.configure('TLabel',background=BG,foreground=INK)
        s.configure('TButton',padding=(12,8),background=WHITE,bordercolor=LINE,lightcolor=WHITE,darkcolor=WHITE)
        s.map('TButton',background=[('active','#E9F5FC')])
        s.configure('Primary.TButton',background=BLUE,foreground=WHITE,bordercolor=BLUE,font=(self.ui_font,10,'bold'))
        s.map('Primary.TButton',background=[('active',NAVY),('disabled','#D6E4EE')],foreground=[('disabled','#7C93A8')])
        s.configure('TEntry',padding=7,fieldbackground=WHITE,bordercolor=LINE)
        s.configure('TCombobox',padding=6,fieldbackground=WHITE,background=WHITE,bordercolor=LINE)
        s.configure('Treeview',rowheight=38,fieldbackground=WHITE,background=WHITE,borderwidth=0,font=(self.ui_font,10))
        s.configure('Treeview.Heading',background='#EAF0F5',foreground=NAVY,padding=(8,10),font=(self.ui_font,10,'bold'),borderwidth=0)
        s.map('Treeview',background=[('selected','#D8F0FC')],foreground=[('selected',NAVY)])
        s.configure('TNotebook',background=WHITE,borderwidth=0)
        s.configure('TNotebook.Tab',padding=(18,10),background='#EAF0F5')
        s.map('TNotebook.Tab',background=[('selected',WHITE)],foreground=[('selected',BLUE)])

    def label(self,parent,text='',size=10,color=INK,bg=WHITE,bold=False,**kwargs):
        return tk.Label(parent,text=text,font=(self.ui_font,size,'bold' if bold else 'normal'),fg=color,bg=bg,**kwargs)

    def button(self,parent,text,command,primary=False):
        return ttk.Button(parent,text=text,command=command,style='Primary.TButton' if primary else 'TButton')

    def build(self):
        side=tk.Frame(self,bg=WHITE,width=216); side.pack(side='left',fill='y'); side.pack_propagate(False)
        self.logo=tk.PhotoImage(data=LOGO_PNG).subsample(3)
        tk.Label(side,image=self.logo,bg=WHITE).pack(anchor='w',padx=28,pady=(12,4))
        self.label(side,'IT ASSET MANAGER',size=10,color=NAVY,bold=True).pack(anchor='w',padx=24)
        self.label(side,'KOREA  /  자산 관리',size=9,color=MUTED).pack(anchor='w',padx=24,pady=(3,16))
        self.nav_buttons={}
        for key,(title,desc,sheet) in PAGES.items():
            if key in ('office','expiry'):
                self.label(side,'자산 목록' if key=='office' else '관리 도구',size=9,color=MUTED).pack(anchor='w',padx=24,pady=(12,4))
            button=tk.Button(side,text=title,anchor='w',font=(self.ui_font,10),bg=WHITE,fg=INK,activebackground='#E6F5FC',activeforeground=NAVY,relief='flat',bd=0,highlightthickness=0,padx=24,pady=8,cursor='hand2',command=lambda p=key:self.navigate(p))
            button.pack(fill='x',padx=8,pady=2); self.nav_buttons[key]=button
        tk.Button(side,text='SAP 자산 대조',anchor='w',font=(self.ui_font,11,'bold'),bg='#E7F5FC',fg=NAVY,relief='flat',bd=0,highlightthickness=0,padx=24,pady=8,cursor='hand2',command=self.open_sap).pack(fill='x',padx=8,pady=(16,2))
        bottom=tk.Frame(side,bg=WHITE); bottom.pack(side='bottom',fill='x',padx=20,pady=22)
        self.button(bottom,'사용 안내',self.help).pack(fill='x')
        self.label(bottom,'EXCEL EDITION  ·  v0.3',size=9,color=MUTED).pack(pady=(12,0))
        main=tk.Frame(self,bg=BG); main.pack(side='left',fill='both',expand=True)
        top=tk.Frame(main,bg=NAVY,height=58); top.pack(fill='x'); top.pack_propagate(False)
        self.label(top,'WORKPLACE  /  IT OPERATIONS',size=10,color=WHITE,bg=NAVY,bold=True).pack(side='left',padx=24)
        self.file_status=self.label(top,'파일을 선택해 주세요',size=10,color='#C7E9FB',bg=NAVY); self.file_status.pack(side='right',padx=20)
        self.content=tk.Frame(main,bg=BG); self.content.pack(fill='both',expand=True,padx=24,pady=(20,12))
        header=tk.Frame(self.content,bg=BG); header.pack(fill='x')
        self.titlelabel=self.label(header,'자산 현황',size=24,bg=BG,bold=True); self.titlelabel.pack(side='left')
        self.button(header,'엑셀 파일 선택',self.choose).pack(side='right',padx=(8,0))
        self.button(header,'새로고침  F5',self.reload).pack(side='right')
        self.description=self.label(self.content,'',color=MUTED,bg=BG,anchor='w'); self.description.pack(fill='x',pady=(5,5))
        self.sync_label=self.label(self.content,'OneDrive 로컬 변경을 3초 간격으로 확인합니다.',size=9,color=MUTED,bg=BG,anchor='w');self.sync_label.pack(fill='x',pady=(0,12))
        self.cards=tk.Frame(self.content,bg=BG); self.cards.pack(fill='x',pady=(0,16))
        self.card_values=[]
        for title,color,target in [('관리 중',BLUE,'overview'),('만료 · 교체 검토',RED,'expired'),('90일 이내',ORANGE,'expiry'),('창고 보관',NAVY,'stock'),('정보 점검',GREEN,'quality')]:
            card=tk.Frame(self.cards,bg=WHITE,highlightbackground=LINE,highlightthickness=1,cursor='hand2')
            card.pack(side='left',expand=True,fill='both',padx=(0,8))
            tk.Frame(card,bg=color,height=3).pack(fill='x')
            lbl=self.label(card,title,size=10,color=MUTED); lbl.pack(anchor='w',padx=15,pady=(12,2))
            val=self.label(card,'—',size=25,color=color,bold=True);val.pack(anchor='w',padx=15,pady=(0,10)); self.card_values.append(val)
            for widget in (card,lbl,val):widget.bind('<Button-1>',lambda e,p=target:self.quick(p))
        self.rolebar=tk.Frame(self.content,bg=BG)
        self.role_buttons={}
        for key in ('office','shared','desktop','stock','retired'):
            b=self.button(self.rolebar,PAGES[key][0],lambda p=key:self.navigate(p)); b.pack(side='left',expand=True,fill='x',padx=(0,6));self.role_buttons[key]=b
        filters=tk.Frame(self.content,bg=WHITE,padx=14,pady=12); filters.pack(fill='x')
        self.label(filters,'통합 검색',color=MUTED).pack(side='left',padx=(0,10))
        self.search=ttk.Entry(filters,textvariable=self.query,width=29); self.search.pack(side='left',fill='x',expand=True,padx=(0,10))
        self.query.trace_add('write',self.schedule_refresh)
        self.locationbox=ttk.Combobox(filters,textvariable=self.location,values=['전체 위치'],width=11,state='readonly');self.locationbox.pack(side='left',padx=4)
        self.kindbox=ttk.Combobox(filters,textvariable=self.kind,values=['전체 종류'],width=10,state='readonly');self.kindbox.pack(side='left',padx=4)
        self.statebox=ttk.Combobox(filters,textvariable=self.state,values=['전체','만료','만료·90일 이내','30일 이내','60일 이내','90일 이내','날짜 미등록','정상','폐기완료'],width=15,state='readonly');self.statebox.pack(side='left',padx=4)
        for box in (self.locationbox,self.kindbox,self.statebox):box.bind('<<ComboboxSelected>>',lambda e:self.refresh())
        self.button(filters,'초기화',self.reset_filters).pack(side='left',padx=(8,0))
        toolbar=tk.Frame(self.content,bg=BG);toolbar.pack(fill='x',pady=12)
        self.listtitle=self.label(toolbar,'자산 목록',size=12,bg=BG,bold=True);self.listtitle.pack(side='left')
        self.button(toolbar,'＋ 자산 등록',self.add,True).pack(side='right')
        self.button(toolbar,'결과 내보내기',self.export).pack(side='right',padx=8)
        self.button(toolbar,'상세 보기',self.edit).pack(side='right')
        tablewrap=tk.Frame(self.content,bg=BG);tablewrap.pack(fill='both',expand=True)
        table=tk.Frame(tablewrap,bg=WHITE);table.pack(side='left',fill='both',expand=True)
        self.columns=['sheet','status','pc','sn','model','location','user','end','days','issue']
        self.tree=ttk.Treeview(table,columns=self.columns,show='headings',selectmode='browse')
        for col,title,width in zip(self.columns,['구분','만료 상태','PC 이름','S/N','모델','위치','사용자','만료일','잔여일','점검 사항'],[90,90,150,120,160,70,100,100,60,200]):
            self.tree.heading(col,text=title,command=lambda c=col:self.sort(c));self.tree.column(col,width=width,minwidth=65,stretch=False)
        self.tree.grid(row=0,column=0,sticky='nsew')
        sy=ttk.Scrollbar(table,orient='vertical',command=self.tree.yview);sy.grid(row=0,column=1,sticky='ns')
        sx=ttk.Scrollbar(table,orient='horizontal',command=self.tree.xview);sx.grid(row=1,column=0,sticky='ew')
        self.tree.configure(yscrollcommand=sy.set,xscrollcommand=sx.set);table.rowconfigure(0,weight=1);table.columnconfigure(0,weight=1)
        for name,bg,fg in [('even',WHITE,INK),('odd','#F7FAFC',INK),('expired','#FFF1EE',RED),('soon','#FFF8E9','#956100')]:self.tree.tag_configure(name,background=bg,foreground=fg)
        self.tree.bind('<Double-1>',lambda e:self.edit());self.tree.bind('<Return>',lambda e:self.edit());self.tree.bind('<<TreeviewSelect>>',self.show_preview)
        self.preview=tk.Frame(tablewrap,bg=WHITE,width=230,highlightbackground=LINE,highlightthickness=1);self.preview.pack(side='right',fill='y',padx=(12,0));self.preview.pack_propagate(False)
        self.label(self.preview,'선택한 자산',size=11,color=MUTED,bold=True).pack(anchor='w',padx=16,pady=(18,12))
        self.preview_title=self.label(self.preview,'목록에서 자산을\n선택하세요',size=14,bold=True,anchor='w',justify='left',wraplength=195);self.preview_title.pack(fill='x',padx=16)
        self.preview_status=self.label(self.preview,'',color=BLUE,anchor='w');self.preview_status.pack(fill='x',padx=16,pady=(8,14))
        self.preview_details=self.label(self.preview,'더블클릭하거나 상세 보기를\n누르면 새 창에서 열립니다.',size=10,color=MUTED,anchor='nw',justify='left',wraplength=195);self.preview_details.pack(fill='both',expand=True,padx=16)
        self.button(self.preview,'새 창에서 상세 보기',self.edit,True).pack(fill='x',padx=12,pady=14)
        self.info=self.label(self.content,'',size=9,color=MUTED,bg=BG,anchor='w');self.info.pack(fill='x',pady=(0,8),before=tablewrap)
        footer=tk.Frame(main,bg=WHITE,highlightbackground=LINE,highlightthickness=1);footer.pack(fill='x',side='bottom',before=self.content)
        self.pending_label=self.label(footer,'저장된 상태',size=10,color=GREEN);self.pending_label.pack(side='left',padx=20,pady=14)
        self.savebutton=self.button(footer,'엑셀에 저장  Ctrl+S',self.save,True);self.savebutton.pack(side='right',padx=16,pady=10)
        self.button(footer,'변경 내역',self.pending_window).pack(side='right')
        tk.Checkbutton(footer,text='자동 저장',variable=self.auto_save,command=self.auto_toggle,bg=WHITE,fg=INK,activebackground=WHITE,selectcolor=WHITE,font=(self.ui_font,10)).pack(side='right',padx=12)
        self.navigate('overview')

    def schedule_refresh(self,*_):
        if self._suspend:return
        if self._search_job:self.after_cancel(self._search_job)
        self._search_job=self.after(150,self.refresh)

    def start(self):
        if self.store:return
        try:
            p=json.loads(CONFIG.read_text(encoding='utf-8')).get('path')
            if p and Path(p).is_file():self.load(p);return
        except Exception:pass
        demo=BASE/'체험용_IT_자산리스트.xlsx'
        if not demo.exists():
            try:
                from create_demo import create_demo
                create_demo(demo)
            except Exception as exc:messagebox.showwarning('체험 파일 생성',f'{exc}\n엑셀 파일 선택으로 시작하세요.',parent=self)
        if demo.exists():self.load(demo)

    def load(self,path):
        try:
            new=Store(path)
            self.adopt_store(new,reset=True)
            self.remember()
        except Exception as exc:messagebox.showerror('불러오기 실패',str(exc),parent=self)

    def discard(self):
        if not self.store or not self.store.pending:return True
        if self._auto_job:self.after_cancel(self._auto_job);self._auto_job=None
        answer=messagebox.askyesno('미저장 변경','저장하지 않은 변경을 모두 버릴까요?',parent=self)
        if not answer:self.queue_auto_save()
        return answer
    def choose(self):
        if not self.discard():return
        p=filedialog.askopenfilename(title='OneDrive 엑셀 파일 선택',filetypes=[('Excel 통합문서','*.xlsx')])
        if p:self.load(p)
    def reload(self):
        if self.store and self.discard():self.load(self.store.path)

    def navigate(self,page):
        self.page=page;title,desc,sheet=PAGES[page];self.titlelabel.configure(text=title);self.description.configure(text=desc)
        for key,b in self.nav_buttons.items():b.configure(bg='#E7F5FC' if key==page else WHITE,fg=NAVY if key==page else INK,font=(self.ui_font,10,'bold' if key==page else 'normal'))
        if page=='overview':self.rolebar.pack(before=self.search.master,fill='x',pady=(0,14))
        else:self.rolebar.pack_forget()
        self.reset_filters()

    def reset_filters(self):
        self._suspend=True;self.query.set('');self.location.set('전체 위치');self.kind.set('전체 종류');self.state.set('만료·90일 이내' if self.page=='expiry' else '전체');self._suspend=False;self.refresh()
    def quick(self,target):
        self.navigate('expiry' if target=='expired' else target)
        if target=='expired':self.state.set('만료');self.refresh()

    def refresh(self):
        self._search_job=None
        if not self.store:return
        rows=self.store.rows();self.issues=checks(self.store,rows);q=self.query.get().strip().casefold();selected=self.state.get();sheet=PAGES[self.page][2]
        active=[i for i in rows if i['sheet']!='폐기완료']
        nums=[len(active),sum(self.store.status(i)=='만료' for i in active),sum(self.store.status(i) in ('30일 이내','60일 이내','90일 이내') for i in active),sum(i['sheet']=='창고(SAP자산)' for i in rows),sum(bool(x) for x in self.issues.values())]
        for label,n in zip(self.card_values,nums):label.configure(text=f'{n:,}')
        for page,b in self.role_buttons.items():b.configure(text=f"{PAGES[page][0]}  {sum(i['sheet']==PAGES[page][2] for i in rows)}")
        keep=self.tree.selection();old=keep[0] if keep else None
        self.tree.delete(*self.tree.get_children());self.items={};self.current_rows=[]
        self.tree.configure(displaycolumns=self.columns if self.page=='quality' else self.columns[:-1])
        for item in rows:
            v=item['values'];status=self.store.status(item);end=self.store.expiry(item);notes=self.issues[(item['sheet'],item['row'])]
            if sheet and item['sheet']!=sheet:continue
            if self.page=='quality' and not notes:continue
            if self.page=='expiry' and item['sheet']=='폐기완료':continue
            if self.location.get()!='전체 위치' and location_key(v.get(8))!=self.location.get():continue
            if self.kind.get()!='전체 종류' and display(v.get(6))!=self.kind.get():continue
            accepted={'만료·90일 이내':['만료','30일 이내','60일 이내','90일 이내'],'90일 이내':['30일 이내','60일 이내','90일 이내'],'60일 이내':['30일 이내','60일 이내']}
            if selected!='전체' and status not in accepted.get(selected,[selected]):continue
            if q and not all(word in ' '.join([item['sheet']]+[display(x) for x in v.values()]+notes).casefold() for word in q.split()):continue
            iid=f"{item['sheet']}:{item['row']}";self.items[iid]=item;self.current_rows.append(item)
            label=next((PAGES[k][0] for k in PAGES if PAGES[k][2]==item['sheet']),item['sheet'])
            days=(end-date.today()).days if end else None
            vals=[label,status,v.get(4),v.get(5),v.get(7),location_key(v.get(8)),user_name(item),end,days if days is not None else '', ' · '.join(notes)]
            tag='expired' if status=='만료' else 'soon' if status in ('30일 이내','60일 이내','90일 이내') else 'even' if len(self.items)%2==0 else 'odd'
            self.tree.insert('','end',iid=iid,values=[display(x) for x in vals],tags=(tag,))
        self.listtitle.configure(text=f"{'점검 필요 자산' if self.page=='quality' else '자산 목록'}  {len(self.items):,}건")
        if self.sort_col:self.order_rows()
        if old in self.items:self.tree.selection_set(old)
        self.show_preview()
        n=len(self.store.pending)
        self.pending_label.configure(text=f'저장 대기 {n}건 · 아직 엑셀에 반영되지 않았습니다' if n else '✓ 모든 변경이 저장되었습니다',fg=ORANGE if n else GREEN)
        self.savebutton.configure(state='normal' if n else 'disabled')
        self.queue_auto_save()
        if self.sap_window and self.sap_window.winfo_exists() and not self.sap_window.loading:self.sap_window.recompare()
        self.info.configure(text=f'조회 {len(self.items):,} / 전체 {len(rows):,}건  ·  날짜 기준 {date.today():%Y-%m-%d}  ·  OneDrive 공유 수정은 한 번에 한 사람씩')

    def sort(self,col):
        self.reverse=not self.reverse if self.sort_col==col else False;self.sort_col=col;self.order_rows()
    def order_rows(self):
        def key(i):
            value=self.tree.set(i,self.sort_col)
            if self.sort_col=='days':
                try:return int(value)
                except ValueError:return 999999
            return value.casefold()
        for pos,i in enumerate(sorted(self.tree.get_children(),key=key,reverse=self.reverse)):self.tree.move(i,'',pos)

    def show_preview(self,event=None):
        ids=self.tree.selection();item=self.items.get(ids[0]) if ids else None;self.selected_item=item
        if not item:
            self.preview_title.configure(text='목록에서 자산을\n선택하세요');self.preview_status.configure(text='');self.preview_details.configure(text='더블클릭하거나 상세 보기를\n누르면 새 창에서 열립니다.');return
        v=item['values'];self.preview_title.configure(text=display(v.get(4) or v.get(7) or v.get(5)))
        status=self.store.status(item);self.preview_status.configure(text=status,fg=RED if status=='만료' else BLUE)
        notes=self.issues.get((item['sheet'],item['row']),[])
        text=f"S/N\n{display(v.get(5)) or '미등록'}\n\n사용자\n{display(user_name(item)) or '미등록'}\n\n위치\n{location_key(v.get(8))}\n\n만료일\n{display(self.store.expiry(item)) or '미등록'}"
        if notes:text+='\n\n점검 필요\n'+' · '.join(notes)
        self.preview_details.configure(text=text)

    def edit(self):
        if not self.selected_item:messagebox.showinfo('자산 선택','먼저 목록에서 자산을 선택하세요.',parent=self);return
        self.open_dialog(self.selected_item)
    def add(self):
        if not self.store:self.choose();return
        self.open_dialog(None)
    def open_dialog(self,item):
        if self.dialog and self.dialog.winfo_exists():self.dialog.lift();self.dialog.focus_force();return
        self.dialog=Editor(self,item)

    def pending_window(self):
        if not self.store:return
        win=tk.Toplevel(self);win.title('저장 전 변경 내역');win.geometry('760x420');win.transient(self);win.grab_set();win.configure(bg=BG)
        self.label(win,'저장 전 변경 내역',size=18,bg=BG,bold=True).pack(anchor='w',padx=20,pady=16)
        box=ttk.Treeview(win,columns=('action','sheet','row'),show='headings')
        for col,title in [('action','작업'),('sheet','시트'),('row','원본 행')]:box.heading(col,text=title)
        box.pack(fill='both',expand=True,padx=20)
        for action,sheet,row in self.store.pending:box.insert('','end',values=(action,sheet,row))
        self.label(win,'새로고침으로 미저장 변경을 모두 취소할 수 있습니다.',color=MUTED,bg=BG).pack(pady=10)
        self.button(win,'닫기',win.destroy).pack(pady=(0,14))

    def save(self,auto=False):
        if self._auto_job:self.after_cancel(self._auto_job)
        self._auto_job=None
        if not self.store or not self.store.pending:return
        if self.dialog and self.dialog.winfo_exists():
            if auto:self._auto_job=self.after(1000,lambda:self.save(auto=True))
            return
        if self.external_changed:
            self.sync_label.configure(text='외부 변경 감지 · 저장을 중지했습니다. 편집 내용을 기록하고 새로고침해 주세요.',fg=ORANGE)
            if not auto:messagebox.showwarning('외부 변경','다른 변경을 덮어쓰지 않도록 저장을 중지했습니다. 편집 내용을 기록한 후 새로고침하세요.',parent=self)
            return
        if not auto and not messagebox.askyesno('공유 엑셀 저장',f'{len(self.store.pending)}건을 저장합니다. 다른 사용자가 수정 중이지 않은지 확인하세요.\n저장 전 원본 백업이 생성됩니다. 계속할까요?',parent=self):return
        try:
            backup=self.store.save();self._auto_failed=False;self.refresh()
            self.sync_label.configure(text=f"{'자동 저장' if auto else '저장'} 완료 {datetime.now():%H:%M:%S} · OneDrive 동기화 완료는 작업 표시줄에서 확인하세요.",fg=GREEN)
            if self.sap_window and self.sap_window.winfo_exists():self.sap_window.recompare()
            if not auto:messagebox.showinfo('저장 완료',f'저장했습니다. OneDrive 동기화 완료를 확인하세요.\n\n백업: {backup}',parent=self)
        except Exception as exc:
            self._auto_failed=True
            self.sync_label.configure(text=f'저장 중지 · {str(exc)[:125]} · 수동 저장으로 재시도하세요.',fg=RED)
            self.pending_label.configure(text='저장되지 않은 변경이 있습니다',fg=RED)
            if not auto:messagebox.showerror('저장 실패',str(exc),parent=self)

    def remember(self):
        CONFIG.parent.mkdir(parents=True,exist_ok=True)
        CONFIG.write_text(json.dumps({'path':str(self.store.path) if self.store else '', 'auto_save':self.auto_save.get()},ensure_ascii=False),encoding='utf-8')

    def auto_toggle(self):
        self._auto_failed=False;self.remember()
        if self.auto_save.get():self.queue_auto_save()
        elif self._auto_job:self.after_cancel(self._auto_job);self._auto_job=None

    def queue_auto_save(self):
        if self.store and self.store.pending and self.auto_save.get() and not self._auto_failed and not self.external_changed and not self._auto_job:
            self._auto_job=self.after(800,lambda:self.save(auto=True))

    def adopt_store(self,new,reset=False):
        self.store=new;self.external_changed=False;self._auto_failed=False
        self.loaded_at=datetime.now().strftime('%H:%M:%S');self.file_status.configure(text=new.path.name+'  ·  '+self.loaded_at+' 불러옴')
        locations=['전체 위치']+sorted({location_key(i['values'].get(8)) for i in new.rows()})
        kinds=['전체 종류']+sorted({display(i['values'].get(6)) for i in new.rows() if i['values'].get(6)})
        self.locationbox.configure(values=locations);self.kindbox.configure(values=kinds)
        if self.location.get() not in locations:self.location.set('전체 위치')
        if self.kind.get() not in kinds:self.kind.set('전체 종류')
        if reset:self.reset_filters()
        else:self.refresh()
        self.sync_label.configure(text='자동 변경 감지 중 · 로컬 파일을 3초 간격으로 확인합니다.',fg=MUTED)
        if self.sap_window and self.sap_window.winfo_exists():self.sap_window.recompare()

    def monitor_tick(self):
        if self.store and not self._watch_inflight and not self._watch_loading:
            path=self.store.path;baseline=self.store.signature;self._watch_inflight=True
            def scan():
                try:self._events.put(('digest',path,baseline,digest(path),None))
                except Exception as exc:self._events.put(('digest',path,baseline,None,str(exc)))
            threading.Thread(target=scan,daemon=True).start()
        self.after(3000,self.monitor_tick)

    def monitor_receive(self):
        while True:
            try:kind,path,baseline,value,error=self._events.get_nowait()
            except queue.Empty:break
            if kind=='digest':self._watch_inflight=False
            else:self._watch_loading=False
            if not self.store or self.store.path!=path or self.store.signature!=baseline:continue
            if error:
                self.sync_label.configure(text='파일 접근 대기 · '+str(error)[:120],fg=ORANGE);continue
            busy=bool(self.store.pending or (self.dialog and self.dialog.winfo_exists()))
            if kind=='reload':
                if busy:
                    self.external_changed=True;self.sync_label.configure(text='외부 변경 감지 · 편집/상세 창을 닫으면 갱신합니다. 미저장 변경이 있으면 먼저 정리하세요.',fg=ORANGE)
                else:
                    self.adopt_store(value);self.sync_label.configure(text=f'외부 변경을 자동 반영했습니다 · {self.loaded_at}',fg=GREEN)
                continue
            action=self._sync_policy.observe(value,baseline,busy)
            self.external_changed=action!='same'
            if action=='same':
                if not self._auto_failed:self.queue_auto_save()
            elif action=='blocked':self.sync_label.configure(text='외부 변경 감지 · 현재 편집 내용은 보존했습니다. 편집 내용을 기록하고 새로고침해 주세요.',fg=ORANGE)
            elif action=='waiting':self.sync_label.configure(text='외부 변경 감지 · 파일이 안정되면 자동 갱신합니다.',fg=BLUE)
            elif action=='reload':
                self._watch_loading=True
                def reload_work(p=path,b=baseline):
                    try:self._events.put(('reload',p,b,Store(p),None))
                    except Exception as exc:self._events.put(('reload',p,b,None,str(exc)))
                threading.Thread(target=reload_work,daemon=True).start()
        self.after(200,self.monitor_receive)

    def open_sap(self):
        if not self.store:self.choose();return
        if self.sap_window and self.sap_window.winfo_exists():self.sap_window.lift();return
        from sap_ui import SapWindow
        self.sap_window=SapWindow(self)

    def export(self):
        if not self.store:return
        p=filedialog.asksaveasfilename(defaultextension='.csv',initialfile=PAGES[self.page][0]+'_'+date.today().isoformat()+'.csv',filetypes=[('CSV','*.csv')])
        if not p:return
        try:
            cols=self.tree.cget('displaycolumns')
            with open(p,'w',newline='',encoding='utf-8-sig') as f:
                writer=csv.writer(f);writer.writerow([self.tree.heading(c)['text'] for c in cols])
                # Prevent spreadsheet formulas when opening CSV in Excel.
                def safe(value):
                    text=str(value)
                    return "'"+text if text.lstrip().startswith(('=','+','@','-')) and not text.lstrip('-').isdigit() else text
                for iid in self.tree.get_children():writer.writerow([safe(self.tree.set(iid,c)) for c in cols])
            messagebox.showinfo('내보내기 완료','현재 검색 결과를 CSV로 저장했습니다.',parent=self)
        except Exception as exc:messagebox.showerror('내보내기 실패',str(exc),parent=self)

    def help(self):
        messagebox.showinfo('사용 안내','① 왼쪽 메뉴에서 사무직·공용·데스크탑 등을 선택합니다.\n② 이름 / PC명 / S/N / SAP번호로 검색합니다.\n③ 자산을 더블클릭하면 상세 조회 창이 열립니다.\n④ 상세 창의 수정 버튼으로 편집하고 변경 적용합니다.\n⑤ 자동 저장이 켜져 있으면 적용 후 자동 저장됩니다. 끄면 하단에서 수동 저장합니다.\n\n교체·만료 관리: 만료 및 30/60/90일 이내 조회\n데이터 점검: 중복, 누락, 날짜와 수식 오류 확인\n창고 이동·폐기: 상세 창 → 이동 / 폐기\n\nF5 새로고침 / Ctrl+F 검색 / Ctrl+S 저장\n\nOneDrive: 한 번에 한 사람만 수정하세요.\n자세한 내용은 프로그램 폴더의 README.md를 참고하세요.',parent=self)
    def close(self):
        if self.dialog and self.dialog.winfo_exists():self.dialog.lift();return
        if self.discard():self.destroy()

class Editor(tk.Toplevel):
    def __init__(self,app,item):
        super().__init__(app);self.app=app;self.item=deepcopy(item);self.fields={};self.editing=item is None;self.dirty=False;self._building=False
        self.title('Knauf | 새 자산 등록' if item is None else 'Knauf | 자산 상세 조회');self.geometry('960x790');self.minsize(880,640);self.configure(bg=BG)
        dialog_height=min(790,max(640,app.winfo_screenheight()-100))
        self.geometry(f'960x{dialog_height}+{app.winfo_rootx()+max(0,(app.winfo_width()-960)//2)}+{app.winfo_rooty()+max(0,(app.winfo_height()-dialog_height)//2)}')
        self.transient(app);self.grab_set();self.protocol('WM_DELETE_WINDOW',self.cancel)
        hero=tk.Frame(self,bg=NAVY,padx=22,pady=18);hero.pack(fill='x')
        app.label(hero,'새 자산 등록' if item is None else display(item['values'].get(4) or item['values'].get(7) or item['values'].get(5)),size=20,bg=NAVY,color=WHITE,bold=True).pack(anchor='w')
        self.sub=app.label(hero,'필수 정보를 입력해 자산을 등록하세요.' if item is None else f"{item['sheet']}  /  {app.store.status(item)}  ·  조회 모드",size=10,bg=NAVY,color='#BFE9FC');self.sub.pack(anchor='w',pady=(5,0))
        tools=tk.Frame(self,bg=BG,padx=20,pady=12);tools.pack(fill='x')
        self.mode_label=app.label(tools,'입력 모드' if self.editing else '조회 모드 · 수정하려면 오른쪽 버튼을 누르세요.',color=BLUE,bg=BG);self.mode_label.pack(side='left')
        self.edit_button=app.button(tools,'수정하기',self.enable_edit,True);self.edit_button.pack(side='right')
        if item is None:self.edit_button.configure(state='disabled')
        else:
            app.button(tools,'이동 / 폐기',self.move_dialog).pack(side='right',padx=8)
            app.button(tools,'삭제',self.delete).pack(side='right')
        self.notebook=ttk.Notebook(self);self.notebook.pack(fill='both',expand=True,padx=20)
        self.tabs={}
        for key,title in [('basic','기본 정보'),('owner','사용자 · 위치'),('expiry','사용기간 · 만료'),('notes','비고 · 점검')]:
            frame=tk.Frame(self.notebook,bg=WHITE,padx=22,pady=18);self.notebook.add(frame,text=title);self.tabs[key]=frame
        self.sheet=tk.StringVar(value=item['sheet'] if item else (PAGES[app.page][2] or app.store.sheets[0]))
        self.build()
        foot=tk.Frame(self,bg=BG,padx=20,pady=16);foot.pack(fill='x')
        app.label(foot,'변경 적용하면 자동 저장됩니다.' if app.auto_save.get() else '변경 적용 후 메인 화면에서 엑셀에 저장하세요.',size=9,color=MUTED,bg=BG).pack(side='left')
        app.button(foot,'닫기',self.cancel).pack(side='right',padx=(8,0))
        self.applybutton=app.button(foot,'변경 적용',self.apply,True);self.applybutton.pack(side='right');self.applybutton.configure(state='normal' if self.editing else 'disabled')

    def build(self):
        self._building=True
        for frame in self.tabs.values():
            for w in frame.winfo_children():w.destroy()
        self.fields={};self.widgets={};app=self.app;sheet=self.sheet.get();vals=self.item['values'] if self.item else {};headers=app.store.headers(sheet)
        app.label(self.tabs['basic'],'자산 구분',size=10,color=MUTED,bold=True).pack(anchor='w')
        selector=ttk.Combobox(self.tabs['basic'],textvariable=self.sheet,values=app.store.sheets,state='disabled' if self.item else 'readonly');selector.pack(fill='x',pady=(5,18));selector.bind('<<ComboboxSelected>>',self.switch_new_sheet)
        groups={'basic':[3,4,5,6,7],'owner':[8,9,10,11,12,13],'expiry':[14,15,16,17],'notes':[18]}
        names={3:'SAP 자산번호',4:'PC 이름',5:'S/N · 시리얼 번호 *',6:'장비 종류',7:'모델',8:'위치 / 사업장',14:'시작일',15:'만료일',16:'사용기간 (개월)',17:'엑셀 잔여개월',18:'비고'}
        for key,cols in groups.items():
            grid=tk.Frame(self.tabs[key],bg=WHITE);grid.pack(fill='x')
            for i,col in enumerate(c for c in cols if c in headers):
                r=i//2*2;c=i%2
                app.label(grid,names.get(col,headers[col]),size=10,color=MUTED,bold=True).grid(row=r,column=c,sticky='w',pady=(8,5),padx=(0,20))
                raw=app.store.book[sheet].cell(self.item['row'],col) if self.item else None
                formula=bool(raw and raw.data_type=='f');value=display(vals.get(col,48 if col==16 else ''))
                var=tk.StringVar(value=value);var.trace_add('write',self.mark_dirty)
                if col==18:
                    entry=tk.Text(grid,height=7,wrap='word',font=(app.ui_font,11),relief='solid',bd=1,highlightthickness=0,padx=10,pady=10)
                    entry.insert('1.0',value);entry.edit_modified(False)
                    entry.bind('<<Modified>>',lambda event:self.note_changed(event.widget))
                elif col==6:
                    entry=ttk.Combobox(grid,textvariable=var,values=['Laptop','Desktop','Monitor','Other'])
                else:entry=ttk.Entry(grid,textvariable=var)
                entry.grid(row=r+1,column=c,columnspan=2 if col==18 else 1,sticky='ew',padx=(0,20),pady=(0,10));self.fields[col]=(var,formula);self.widgets[col]=entry
                if formula:
                    app.label(grid,'수식 · 읽기 전용',size=9,color=MUTED).grid(row=r,column=c,sticky='e',padx=(0,22))
            grid.columnconfigure(0,weight=1);grid.columnconfigure(1,weight=1)
        exp=self.tabs['expiry']
        self.calcbutton=app.button(exp,'시작일 + 사용기간으로 만료일 계산',self.calculate);self.calcbutton.pack(anchor='w',pady=16)
        if self.item:
            end=app.store.expiry(self.item);status=app.store.status(self.item)
            app.label(exp,f"만료 상태   {status}\n만료일   {display(end) or '미등록'}",size=14,color=RED if status=='만료' else NAVY,bold=True,justify='left').pack(anchor='w',pady=10)
        app.label(exp,'날짜 형식: YYYY-MM-DD  /  만료는 엑셀 만료일 기준입니다.\n만료일이 없으면 유효한 시작일과 사용기간으로 판단합니다.',size=10,color=MUTED,justify='left').pack(anchor='w',pady=12)
        notes=self.tabs['notes'];issues=checks(app.store,[*app.store.rows()]).get((sheet,self.item['row']),[]) if self.item else []
        app.label(notes,'점검 사항',size=12,bold=True).pack(anchor='w',pady=(25,10))
        app.label(notes,'\n'.join('• '+n for n in issues) or '현재 확인된 점검 사항이 없습니다.',color=ORANGE if issues else GREEN,justify='left').pack(anchor='w')
        if self.item:app.label(notes,f"원본: {sheet} / {self.item['row']}행\nNo.: {display(vals.get(2))}",size=9,color=MUTED,justify='left').pack(anchor='w',pady=24)
        self.update_state();self._building=False

    def note_changed(self,widget):
        if widget.edit_modified():
            self.mark_dirty();widget.edit_modified(False)

    def mark_dirty(self,*_):
        if not self._building:self.dirty=True
    def switch_new_sheet(self,event):
        # Preserve entered values by header name when changing the category of a new record.
        values={self.app.store.headers(self._old_sheet).get(c):var.get() for c,(var,_) in self.fields.items()} if hasattr(self,'_old_sheet') else {}
        self.build()
        for c,(var,formula) in self.fields.items():
            label=self.app.store.headers(self.sheet.get()).get(c)
            if label in values:var.set(values[label])
        self._old_sheet=self.sheet.get()
    def update_state(self):
        for col,widget in self.widgets.items():
            formula=self.fields[col][1]
            writable=self.editing and not formula and col!=17
            widget.configure(state='normal' if writable else 'disabled' if isinstance(widget,(tk.Text,ttk.Combobox)) else 'readonly')
        self.calcbutton.configure(state='normal' if self.editing else 'disabled')
        self._old_sheet=self.sheet.get()
    def enable_edit(self):
        self.editing=True;self.update_state();self.mode_label.configure(text='수정 모드 · 변경 후 변경 적용을 누르세요.');self.edit_button.configure(state='disabled');self.applybutton.configure(state='normal')
    def calculate(self):
        try:
            if self.fields[15][1]:raise ValueError('만료일이 기존 수식입니다. 엑셀에서 재계산됩니다.')
            start=as_date(self.fields[14][0].get());months=int(self.fields[16][0].get())
            if not start or not 1<=months<=1200:raise ValueError('시작일과 사용기간(1~1200개월)을 확인하세요.')
            self.fields[15][0].set(display(add_months(start,months)))
        except Exception as exc:messagebox.showerror('계산 확인',str(exc),parent=self)

    def read_fields(self):
        fields={}
        for col,(var,formula) in self.fields.items():
            if formula or col==17:continue
            value=(self.widgets[col].get('1.0','end-1c') if isinstance(self.widgets[col],tk.Text) else var.get()).strip();original=self.item['values'].get(col) if self.item else None
            if self.item and value==display(original):continue
            if col in (14,15) and value:
                parsed=as_date(value)
                if not parsed and not(col==14 and value=='미취득'):raise ValueError('날짜는 YYYY-MM-DD로 입력하세요. 시작일은 미취득도 가능합니다.')
                value=parsed or value
            if col==16 and value:
                value=int(value)
                if not 1<=value<=1200:raise ValueError('사용기간은 1~1200개월입니다.')
            if isinstance(value,str) and value.startswith('='):raise ValueError('수식은 일반 입력란에 입력할 수 없습니다.')
            fields[col]=value if value!='' else None
        if 5 not in fields:fields[5]=self.item['values'].get(5) if self.item else None
        if not display(fields[5]).strip():raise ValueError('S/N은 필수입니다.')
        start=as_date(fields.get(14,self.item['values'].get(14) if self.item else None));end=as_date(fields.get(15,self.item['values'].get(15) if self.item else None))
        if start and end and end<start:raise ValueError('만료일이 시작일보다 빠릅니다.')
        return fields

    def apply(self):
        try:
            self.app.store.apply(self.sheet.get(),self.item['row'] if self.item else None,self.read_fields());self.app.refresh();self.destroy()
        except Exception as exc:messagebox.showerror('입력 확인',str(exc),parent=self)
    def cancel(self):
        if self.dirty and not messagebox.askyesno('편집 취소','이 창에서 입력한 변경을 버릴까요?',parent=self):return
        self.destroy()
    def delete(self):
        if not self.item:return
        if messagebox.askyesno('자산 삭제',f"S/N {display(self.item['values'].get(5))}\n이 자산을 삭제할까요?\n폐기 이력을 남기려면 삭제 대신 이동 / 폐기를 사용하세요.\n저장 후 복구는 백업 파일로 가능합니다.",parent=self):
            self.app.store.delete(self.item['sheet'],self.item['row']);self.app.refresh();self.destroy()
    def move_dialog(self):
        if self.dirty:
            messagebox.showinfo('편집 중','먼저 변경 적용 후 상세 창을 다시 열어 이동하세요.',parent=self);return
        win=tk.Toplevel(self);win.title('자산 이동 / 폐기');win.geometry('540x380');win.transient(self);win.grab_set();win.configure(bg=BG)
        self.app.label(win,'자산 이동 / 폐기',size=18,bg=BG,bold=True).pack(anchor='w',padx=22,pady=20)
        self.app.label(win,'이동할 구분을 선택하세요. 원본 시트에서 이동됩니다.',bg=BG).pack(anchor='w',padx=22)
        target=tk.StringVar(value='창고(SAP자산)' if self.item['sheet']!='창고(SAP자산)' else '사무직 List')
        ttk.Combobox(win,textvariable=target,values=[s for s in self.app.store.sheets if s!=self.item['sheet']],state='readonly').pack(fill='x',padx=22,pady=18)
        self.app.label(win,'폐기완료 선택 시 만료 관리 대상에서 제외됩니다.\n기존 사용자·장비 정보는 유지합니다.\n새 시트에 없는 항목은 비고에 보관합니다.',color=MUTED,bg=BG,justify='left').pack(anchor='w',padx=22)
        def perform():
            if not messagebox.askyesno('이동 확인',f"{self.item['sheet']} → {target.get()}\n이동할까요? 자동 저장이 켜져 있으면 적용 후 저장됩니다.",parent=win):return
            try:
                self.app.store.relocate(self.item['sheet'],self.item['row'],target.get());self.app.refresh();win.destroy();self.destroy()
            except Exception as exc:messagebox.showerror('이동 실패',str(exc),parent=win)
        self.app.button(win,'이동 적용',perform,True).pack(side='right',padx=22,pady=20)
        self.app.button(win,'취소',win.destroy).pack(side='right',pady=20)
        def closemove():win.destroy();self.grab_set()
        win.protocol('WM_DELETE_WINDOW',closemove)
        win.bind('<Destroy>',lambda e:self.grab_set() if e.widget is win and self.winfo_exists() else None)

if __name__=='__main__':
    app=App()
    def on_error(kind,error,tb):
        log=CONFIG.parent/'error.log';log.parent.mkdir(parents=True,exist_ok=True);log.write_text(''.join(traceback.format_exception(kind,error,tb)),encoding='utf-8')
        messagebox.showerror('오류',f'{error}\n\n오류 기록: {log}',parent=app)
    app.report_callback_exception=on_error
    app.mainloop()
