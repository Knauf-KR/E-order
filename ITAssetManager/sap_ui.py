"""SAP comparison window. Source spreadsheets remain read-only."""
import csv, threading, queue
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from reconcile import SapBook, compare, STATUSES
from storage import display

class SapWindow(tk.Toplevel):
    def __init__(self,app):
        super().__init__(app);self.app=app;self.sap=None;self.results=[];self.visible={};self.jobs=queue.Queue();self.loading=False;self.stale=False
        from app import NAVY, BLUE, WHITE, BG, MUTED
        self.title('Knauf | SAP 자산 대조');self.geometry(f'{min(1400,self.winfo_screenwidth()-60)}x{min(860,self.winfo_screenheight()-80)}');self.minsize(1080,650);self.configure(bg=BG);self.transient(app)
        top=tk.Frame(self,bg=NAVY,padx=22,pady=18);top.pack(fill='x')
        app.label(top,'SAP 자산 대조',size=22,color=WHITE,bg=NAVY,bold=True).pack(anchor='w')
        app.label(top,'SAP Asset List의 S/N과 현재 IT 목록을 양방향으로 확인합니다.',color='#BFE9FC',bg=NAVY).pack(anchor='w',pady=(6,0))
        bar=tk.Frame(self,bg=BG,padx=20,pady=14);bar.pack(fill='x')
        self.upload=app.button(bar,'SAP 엑셀 선택',self.choose,True);self.upload.pack(side='left')
        self.sheet=tk.StringVar();self.sheetbox=ttk.Combobox(bar,textvariable=self.sheet,state='disabled',width=18);self.sheetbox.pack(side='left',padx=12);self.sheetbox.bind('<<ComboboxSelected>>',lambda e:self.recompare())
        self.rerun=app.button(bar,'다시 대조',self.recompare);self.rerun.pack(side='left')
        self.filelabel=app.label(bar,'파일을 선택하면 회계 시트를 선택할 수 있습니다.',bg=BG,color=MUTED,anchor='w');self.filelabel.pack(side='left',padx=14)
        self.notice=app.label(self,'K-GAAP / IFRS / HGB는 한 시트씩 대조합니다. 결과는 업로드된 SAP 파일 기준이며 SAP 시스템을 직접 조회하지 않습니다.',bg=BG,color=MUTED,anchor='w',justify='left',wraplength=1150);self.notice.pack(fill='x',padx=22)
        self.summary=app.label(self,'SAP 파일을 선택하세요.',size=13,bg=BG,color=NAVY,bold=True,anchor='w');self.summary.pack(fill='x',padx=22,pady=14)
        filters=tk.Frame(self,bg=WHITE,padx=12,pady=12);filters.pack(fill='x',padx=20)
        app.label(filters,'검색').pack(side='left',padx=(0,10));self.query=tk.StringVar();ttk.Entry(filters,textvariable=self.query,width=35).pack(side='left',fill='x',expand=True)
        self.query.trace_add('write',lambda *_:self.render())
        self.status=tk.StringVar(value='확인 필요');status=ttk.Combobox(filters,textvariable=self.status,values=['확인 필요','전체(대상외 제외)']+STATUSES,state='readonly',width=23);status.pack(side='left',padx=12);status.bind('<<ComboboxSelected>>',lambda e:self.render())
        app.button(filters,'결과 내보내기',self.export).pack(side='right')
        self.table=tk.Frame(self,bg=BG);self.table.pack(fill='both',expand=True,padx=20,pady=14)
        self.cols=['direction','status','asset','serial','type','description','where','notes']
        self.tree=ttk.Treeview(self.table,columns=self.cols,show='headings')
        for c,title,width in zip(self.cols,['방향','대조 결과','SAP 자산번호','S/N','장비 종류','SAP 자산 설명 / IT 모델','발견한 IT 위치','확인 내용'],[100,150,110,135,90,340,220,300]):
            self.tree.heading(c,text=title);self.tree.column(c,width=width,stretch=False)
        self.tree.grid(row=0,column=0,sticky='nsew');sy=ttk.Scrollbar(self.table,orient='vertical',command=self.tree.yview);sy.grid(row=0,column=1,sticky='ns');sx=ttk.Scrollbar(self.table,orient='horizontal',command=self.tree.xview);sx.grid(row=1,column=0,sticky='ew');self.tree.configure(yscrollcommand=sy.set,xscrollcommand=sx.set);self.table.rowconfigure(0,weight=1);self.table.columnconfigure(0,weight=1)
        self.tree.tag_configure('ok',foreground='#287A56');self.tree.tag_configure('review',foreground='#9B5C00',background='#FFF8E9')
        self.tree.bind('<Double-1>',lambda e:self.detail())
        footer=tk.Frame(self,bg=BG,padx=20,pady=12);footer.pack(fill='x',side='bottom',before=self.table)
        self.count=app.label(footer,'',size=9,bg=BG,color=MUTED,anchor='w');self.count.pack(side='left')
        app.button(footer,'선택 결과 상세',self.detail).pack(side='right');self.after(200,self.receive)

    def choose(self):
        path=filedialog.askopenfilename(parent=self,title='SAP Asset List 선택',filetypes=[('Excel 통합문서','*.xlsx')])
        if path:self.load(path)

    def load(self,path):
        if self.loading:return
        self.loading=True;self.stale=True;self.upload.configure(state='disabled');self.sheetbox.configure(state='disabled');self.rerun.configure(state='disabled')
        self.filelabel.configure(text='SAP 파일을 읽는 중…');self.notice.configure(text='새 파일을 확인하는 동안 이전 결과를 숨겼습니다. 원본 파일은 수정하지 않습니다.')
        self.tree.delete(*self.tree.get_children());self.visible={};self.results=[]
        def work():
            try:self.jobs.put((SapBook(path),None))
            except Exception as exc:self.jobs.put((None,str(exc)))
        threading.Thread(target=work,daemon=True).start()

    def receive(self):
        try:
            sap,error=self.jobs.get_nowait();self.loading=False;self.upload.configure(state='normal');self.rerun.configure(state='normal')
            if error:
                self.sap=None;self.results=[];self.filelabel.configure(text='불러오기 실패');self.summary.configure(text='SAP 파일을 다시 선택하세요.');messagebox.showerror('SAP 파일 확인',error,parent=self)
            else:
                self.sap=sap;names=list(sap.sheets);self.sheetbox.configure(values=names,state='readonly');self.sheet.set('K-GAAP' if 'K-GAAP' in names else names[0]);self.filelabel.configure(text=sap.path.name);self.recompare()
        except queue.Empty:pass
        self.after(200,self.receive)

    def recompare(self):
        if not self.sap or self.loading:return
        self.results=compare(self.sap.sheets[self.sheet.get()],self.app.store.rows());self.stale=False
        self.compared_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        pending='미저장 변경 포함' if self.app.store.pending else '저장된 IT 목록'
        self.notice.configure(text=f'{self.compared_at} 대조 · {pending} · SAP {self.sheet.get()} 시트 기준. S/N의 공백·대소문자만 정규화하며 O/0 등은 바꾸지 않습니다.')
        target=[r for r in self.results if r['direction']=='SAP → IT' and r['status']!='대상외'];ok=sum(r['status']=='일치' for r in target);no_sn=sum(r['status']=='S/N 확인 필요' for r in target);excluded=sum(r['status']=='대상외' for r in self.results)
        self.summary.configure(text=f'SAP PC 대상 {len(target):,}건  ·  일치 {ok:,}  ·  확인 필요 {len(target)-ok:,}  ·  S/N 확인 필요 {no_sn:,}  ·  대상외 {excluded:,}')
        self.render()

    def render(self):
        self.tree.delete(*self.tree.get_children());self.visible={};q=self.query.get().strip().casefold();selected=self.status.get()
        for i,r in enumerate(self.results):
            status=r['status']
            if selected=='확인 필요' and status in ('일치','대상외'):continue
            if selected=='전체(대상외 제외)' and status=='대상외':continue
            if selected not in ('확인 필요','전체(대상외 제외)') and status!=selected:continue
            where=' / '.join(f"{m['sheet']} {m['row']}행" for m in r['matches'])
            vals=[r['direction'],status,r['asset'],r['serial'],r['type'],r['description'],where,r['notes']]
            if q and not all(word in ' '.join(vals).casefold() for word in q.split()):continue
            iid=str(i);self.visible[iid]=r;self.tree.insert('','end',iid=iid,values=vals,tags=('ok' if status=='일치' else 'review',))
        self.count.configure(text=f'조회 {len(self.visible):,}건 / 전체 결과 {len(self.results):,}건 · 원본은 수정하지 않습니다.')

    def detail(self):
        selected=self.tree.selection()
        if not selected:return
        r=self.visible[selected[0]];win=tk.Toplevel(self);win.title('대조 결과 상세');win.geometry('850x650');win.transient(self)
        text=tk.Text(win,wrap='word',font=(self.app.ui_font,11),padx=20,pady=20);text.pack(fill='both',expand=True)
        lines=[r['status'],f"방향: {r['direction']}",f"S/N: {r['serial'] or '확인 필요'}",f"SAP 자산번호: {r['asset']}",f"설명: {r['description']}",f"SAP 원본: {r['sap_source']}",f"추출 방식: {r['method']}",f"판정 내용: {r['notes']}",'','발견한 IT 목록']
        for m in r['matches']:
            v=m['values'];lines.append(f"{m['sheet']} / {m['row']}행\nPC명: {display(v.get(4))}\nS/N: {display(v.get(5))}\nSAP번호: {display(v.get(3))}\n모델: {display(v.get(7))}\n")
        text.insert('1.0','\n'.join(lines));text.configure(state='disabled')

    def export(self):
        if not self.results or self.loading:return
        path=filedialog.asksaveasfilename(parent=self,defaultextension='.csv',initialfile='SAP_대조결과.csv',filetypes=[('CSV','*.csv')])
        if not path:return
        try:
            def safe(value):
                text=display(value)
                return "'"+text if text.lstrip().startswith(('=','+','-','@')) else text
            with open(path,'w',newline='',encoding='utf-8-sig') as f:
                w=csv.writer(f);w.writerow(['대조시각','SAP파일','회계시트','IT파일','방향','결과','SAP자산번호','S/N','종류','설명','SAP원본행','추출방식','IT발견위치','확인내용'])
                for iid in self.tree.get_children():
                    r=self.visible[iid];w.writerow([safe(x) for x in [self.compared_at,self.sap.path.name,self.sheet.get(),self.app.store.path.name,r['direction'],r['status'],r['asset'],r['serial'],r['type'],r['description'],r['sap_source'],r['method'],' / '.join(f"{m['sheet']} {m['row']}행" for m in r['matches']),r['notes']]])
            messagebox.showinfo('내보내기','현재 필터 결과를 저장했습니다.',parent=self)
        except Exception as exc:messagebox.showerror('내보내기 실패',str(exc),parent=self)
