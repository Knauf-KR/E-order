import os, sys, json, csv, traceback
from pathlib import Path
from datetime import date
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font
from storage import Store, as_date, display, add_months

BASE = Path(__file__).resolve().parent
CONFIG = Path(os.environ.get('LOCALAPPDATA',Path.home())) / 'ITAssetManager' / 'settings.json'

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('IT 자산 관리 · Excel Edition')
        self.geometry('1400x850'); self.minsize(1050,650)
        self.configure(bg='#f3f6fa')
        self.store = None; self.items = {}; self.sort_reverse = False
        families = set(font.families(self))
        self.ui_font = next((f for f in ['맑은 고딕','Malgun Gothic','Noto Sans CJK KR','Arial'] if f in families), 'TkDefaultFont')
        style = ttk.Style(self); style.theme_use('clam')
        style.configure('.',font=(self.ui_font,10))
        style.configure('TFrame',background='#f3f6fa')
        style.configure('TLabel',background='#f3f6fa',foreground='#172d47')
        style.configure('TButton',padding=(13,8))
        style.configure('Accent.TButton',background='#1769aa',foreground='white')
        style.configure('Treeview',rowheight=32,fieldbackground='white',background='white')
        style.configure('Treeview.Heading',padding=8,background='#e5ecf5',font=(self.ui_font,10,'bold'))
        outer=ttk.Frame(self,padding=22); outer.pack(fill='both',expand=True)
        head=ttk.Frame(outer); head.pack(fill='x')
        ttk.Label(head,text='IT 자산 관리',font=(self.ui_font,23,'bold')).pack(side='left')
        ttk.Label(head,text='EXCEL EDITION  /  v0.1',foreground='#64809c').pack(side='left',padx=18)
        ttk.Button(head,text='엑셀 파일 선택',command=self.choose).pack(side='right')
        self.pathlabel=ttk.Label(outer,text='엑셀 파일을 선택해 시작하세요.',foreground='#64809c')
        self.pathlabel.pack(fill='x',pady=(10,12))
        self.cards=ttk.Frame(outer); self.cards.pack(fill='x',pady=8)
        self.card_labels=[]
        for title,filterval in [('전체 자산','전체'),('만료','만료'),('90일 이내 만료','90일 이내'),('날짜 미등록','날짜 미등록'),('폐기완료','폐기완료')]:
            b=ttk.Button(self.cards,text=title+'\n—',command=lambda f=filterval:self.quick(f))
            b.pack(side='left',expand=True,fill='x',padx=4); self.card_labels.append((b,title))
        bar=ttk.Frame(outer); bar.pack(fill='x',pady=14)
        self.query=tk.StringVar(); self.query.trace_add('write',lambda *_:self.refresh())
        ttk.Label(bar,text='통합 검색').pack(side='left')
        ttk.Entry(bar,textvariable=self.query,width=31).pack(side='left',padx=(8,16))
        self.group=tk.StringVar(value='전체 시트'); self.state=tk.StringVar(value='전체'); self.location=tk.StringVar(value='전체 위치')
        for variable,values,width in [(self.group,['전체 시트'],18),(self.state,['전체','만료','30일 이내','60일 이내','90일 이내','날짜 미등록','정상','폐기완료'],16),(self.location,['전체 위치'],15)]:
            box=ttk.Combobox(bar,textvariable=variable,values=values,state='readonly',width=width)
            box.pack(side='left',padx=4); box.bind('<<ComboboxSelected>>',lambda e:self.refresh())
            if variable is self.group: self.groupbox=box
            if variable is self.location: self.locbox=box
        ttk.Button(bar,text='초기화',command=self.reset).pack(side='left',padx=6)
        actions=ttk.Frame(outer); actions.pack(fill='x',pady=(0,10))
        for text,cmd in [('＋ 자산 등록',self.add),('상세 / 수정',self.edit),('삭제',self.delete),('다시 불러오기',self.reload),('검색 결과 CSV',self.export)]:
            ttk.Button(actions,text=text,command=cmd).pack(side='left',padx=(0,6))
        self.savebutton=ttk.Button(actions,text='엑셀에 저장',style='Accent.TButton',command=self.save)
        self.savebutton.pack(side='right')
        panel=ttk.Frame(outer); panel.pack(fill='both',expand=True)
        self.columns=['sheet','status','pc','sn','model','location','user','end','days']
        self.tree=ttk.Treeview(panel,columns=self.columns,show='headings',selectmode='browse')
        titles=['구분 / 시트','만료 상태','PC Name','S/N','모델','위치','사용자','만료일','잔여일']
        for col,title,width in zip(self.columns,titles,[135,100,175,135,220,95,120,105,70]):
            self.tree.heading(col,text=title,command=lambda c=col:self.sort(c)); self.tree.column(col,width=width,minwidth=65)
        self.tree.grid(row=0,column=0,sticky='nsew')
        ttk.Scrollbar(panel,orient='vertical',command=self.tree.yview).grid(row=0,column=1,sticky='ns')
        sx=ttk.Scrollbar(panel,orient='horizontal',command=self.tree.xview); sx.grid(row=1,column=0,sticky='ew')
        self.tree.configure(yscrollcommand=lambda a,b:panel.grid_slaves(row=0,column=1)[0].set(a,b),xscrollcommand=sx.set)
        panel.rowconfigure(0,weight=1); panel.columnconfigure(0,weight=1)
        self.tree.tag_configure('expired',foreground='#b73838',background='#fff4f2')
        self.tree.tag_configure('soon',foreground='#885800',background='#fff9e8')
        self.tree.bind('<Double-1>',lambda e:self.edit())
        self.info=ttk.Label(outer,text=''); self.info.pack(anchor='w',pady=(10,5))
        ttk.Label(outer,text='OneDrive: 한 번에 한 사람만 수정하고 동기화 완료 후 다음 사람이 사용하세요. 만료 기준: 엑셀의 만료일 / 오늘 날짜.',foreground='#697c90').pack(anchor='w')
        self.protocol('WM_DELETE_WINDOW',self.close)
        self.bind('<Control-s>',lambda e:self.save())
        self.bind('<Control-f>',lambda e: self.focus_search(bar))
        self.after(100,self.start)

    def focus_search(self,bar):
        for child in bar.winfo_children():
            if isinstance(child,ttk.Entry): child.focus_set(); child.select_range(0,'end'); break

    def start(self):
        try:
            path=json.loads(CONFIG.read_text(encoding='utf-8')).get('path')
            if path and Path(path).is_file(): self.load(path); return
        except Exception: pass
        demo=BASE/'체험용_IT_자산리스트.xlsx'
        if not demo.exists():
            try:
                from create_demo import create_demo
                create_demo(demo)
            except Exception as exc:
                messagebox.showwarning('체험 파일 생성', f'체험 파일을 만들지 못했습니다: {exc}\n엑셀 파일 선택으로 파일을 열어주세요.', parent=self)
        if demo.exists(): self.load(demo)

    def discard(self):
        return not self.store or not self.store.pending or messagebox.askyesno('미저장 변경','저장하지 않은 변경을 버리시겠습니까?',parent=self)

    def load(self,path):
        try:
            new=Store(path)
            CONFIG.parent.mkdir(parents=True,exist_ok=True)
            CONFIG.write_text(json.dumps({'path':str(new.path)},ensure_ascii=False),encoding='utf-8')
            self.store=new; self.pathlabel.configure(text=str(new.path))
            self.groupbox.configure(values=['전체 시트']+new.sheets)
            locations=sorted({str(i['values'].get(8)) for i in new.rows() if i['values'].get(8)})
            self.locbox.configure(values=['전체 위치']+locations)
            self.reset()
        except Exception as exc: messagebox.showerror('불러오기 실패',str(exc),parent=self)

    def choose(self):
        if not self.discard(): return
        p=filedialog.askopenfilename(title='OneDrive 엑셀 파일 선택',filetypes=[('Excel 통합문서','*.xlsx')])
        if p: self.load(p)

    def reload(self):
        if self.store and self.discard(): self.load(self.store.path)

    def reset(self):
        self.group.set('전체 시트'); self.state.set('전체'); self.location.set('전체 위치'); self.query.set(''); self.refresh()

    def quick(self,value):
        self.group.set('전체 시트'); self.location.set('전체 위치'); self.query.set(''); self.state.set(value); self.refresh()

    def refresh(self):
        if not self.store: return
        rows=self.store.rows(); q=self.query.get().strip().casefold(); selected=self.state.get()
        counts=[len(rows),0,0,0,0]
        self.tree.delete(*self.tree.get_children()); self.items={}
        for item in rows:
            v=item['values']; state=self.store.status(item); end=self.store.expiry(item)
            days=(end-date.today()).days if end else None
            if state=='만료': counts[1]+=1
            if state in ('30일 이내','60일 이내','90일 이내'): counts[2]+=1
            if state=='날짜 미등록': counts[3]+=1
            if state=='폐기완료': counts[4]+=1
            if self.group.get()!='전체 시트' and item['sheet']!=self.group.get(): continue
            if self.location.get()!='전체 위치' and str(v.get(8))!=self.location.get(): continue
            if selected=='90일 이내':
                if state not in ('30일 이내','60일 이내','90일 이내'): continue
            elif selected=='60일 이내':
                if state not in ('30일 이내','60일 이내'): continue
            elif selected!='전체' and state!=selected: continue
            if q and q not in ' '.join([item['sheet']]+[display(x) for x in v.values()]).casefold(): continue
            iid=f"{item['sheet']}:{item['row']}"; self.items[iid]=item
            vals=[item['sheet'],state,v.get(4),v.get(5),v.get(7),v.get(8),v.get(9) or v.get(10) or v.get(12),display(end),days if days is not None else '']
            tag='expired' if state=='만료' else 'soon' if state in ('30일 이내','60일 이내','90일 이내') else ''
            self.tree.insert('', 'end',iid=iid,values=[display(x) for x in vals],tags=(tag,))
        for (button,title),count in zip(self.card_labels,counts): button.configure(text=f'{title}\n{count:,}건')
        n=len(self.store.pending)
        self.info.configure(text=f'조회 {len(self.items):,}건 / 전체 {len(rows):,}건     ·     '+(f'미저장 작업 {n}건 — 엑셀에 저장을 눌러 반영하세요.' if n else '저장된 상태'))
        self.savebutton.configure(text=f'엑셀에 저장 ({n})' if n else '엑셀에 저장',state='normal' if n else 'disabled')

    def sort(self,col):
        self.sort_reverse=not self.sort_reverse
        def key(i):
            value=self.tree.set(i,col)
            if col=='days':
                try: return int(value)
                except ValueError: return 999999
            return value.casefold()
        for pos,iid in enumerate(sorted(self.tree.get_children(),key=key,reverse=self.sort_reverse)): self.tree.move(iid,'',pos)

    def selected(self):
        s=self.tree.selection()
        if not s: messagebox.showinfo('자산 선택','목록에서 자산을 먼저 선택하세요.',parent=self); return None
        return self.items[s[0]]

    def add(self):
        if self.store: Editor(self,None)
        else: self.choose()

    def edit(self):
        if not self.store: return
        item=self.selected()
        if item: Editor(self,item)

    def delete(self):
        if not self.store: return
        item=self.selected()
        if item and messagebox.askyesno('삭제 확인',f"S/N: {display(item['values'].get(5))}\n이 자산을 삭제할까요?\n저장 전에는 다시 불러오기로 취소할 수 있습니다.\n저장 후에는 자동 백업에서 복구할 수 있습니다.",parent=self):
            self.store.delete(item['sheet'],item['row']); self.refresh()

    def save(self):
        if not self.store or not self.store.pending: return
        if not messagebox.askyesno('공유 엑셀 저장',f'{len(self.store.pending)}건의 작업을 원본 엑셀에 반영합니다.\n다른 사용자가 수정 중이지 않은지 확인하세요.\n저장 전 원본 백업이 생성됩니다. 계속할까요?',parent=self): return
        try:
            backup=self.store.save(); self.refresh()
            messagebox.showinfo('저장 완료',f'저장했습니다. OneDrive 동기화 완료를 확인하세요.\n\n백업: {backup}',parent=self)
        except Exception as exc: messagebox.showerror('저장하지 못했습니다',str(exc),parent=self)

    def export(self):
        if not self.store: return
        p=filedialog.asksaveasfilename(defaultextension='.csv',initialfile='자산_검색결과.csv',filetypes=[('CSV','*.csv')])
        if p:
            try:
                with open(p,'w',newline='',encoding='utf-8-sig') as f:
                    writer=csv.writer(f); writer.writerow([self.tree.heading(c)['text'] for c in self.columns])
                    writer.writerows(self.tree.item(i)['values'] for i in self.tree.get_children())
                messagebox.showinfo('내보내기','검색 결과를 저장했습니다.',parent=self)
            except Exception as exc: messagebox.showerror('내보내기 실패',str(exc),parent=self)

    def close(self):
        if self.discard(): self.destroy()

class Editor(tk.Toplevel):
    def __init__(self,app,item):
        super().__init__(app); self.app=app; self.item=item; self.fields={}
        self.title('자산 상세 / 수정' if item else '새 자산 등록'); self.geometry('860x720'); self.minsize(800,700)
        self.transient(app); self.grab_set()
        body=ttk.Frame(self,padding=20); body.pack(fill='both',expand=True)
        ttk.Label(body,text='자산 상세' if item else '새 자산 등록',font=(app.ui_font,18,'bold')).pack(anchor='w',pady=(0,10))
        ttk.Label(body,text='* S/N 필수 · 날짜 형식 YYYY-MM-DD · 기존 수식은 읽기 전용').pack(anchor='w',pady=5)
        self.sheet=tk.StringVar(value=item['sheet'] if item else (app.group.get() if app.group.get() in app.store.sheets else app.store.sheets[0]))
        selector=ttk.Combobox(body,textvariable=self.sheet,values=app.store.sheets,state='disabled' if item else 'readonly')
        selector.pack(fill='x',pady=8); selector.bind('<<ComboboxSelected>>',lambda e:self.build())
        self.gridbox=ttk.Frame(body); self.gridbox.pack(fill='both',expand=True)
        self.build()
        actions=ttk.Frame(body); actions.pack(fill='x',pady=(12,0))
        ttk.Button(actions,text='취소',command=self.destroy).pack(side='right',padx=8)
        ttk.Button(actions,text='변경 적용 (아직 엑셀에 저장 안 됨)',command=self.apply,style='Accent.TButton').pack(side='right')

    def build(self):
        for w in self.gridbox.winfo_children(): w.destroy()
        self.fields={}; sheet=self.sheet.get(); book=self.app.store.book
        vals=self.item['values'] if self.item else {}
        for i,(col,label) in enumerate(self.app.store.headers(sheet).items()):
            row=i//2; side=(i%2)*2
            ttk.Label(self.gridbox,text=label+(' *' if col==5 else '')).grid(row=row,column=side,sticky='w',padx=(0,8),pady=9)
            raw=book[sheet].cell(self.item['row'],col) if self.item else None
            formula=bool(raw and raw.data_type=='f')
            value=display(vals.get(col,48 if col==16 else ''))
            var=tk.StringVar(value=value)
            entry=ttk.Entry(self.gridbox,textvariable=var,width=27)
            entry.grid(row=row,column=side+1,sticky='ew',padx=(0,16),pady=9)
            if col in (2,17) or formula: entry.configure(state='readonly')
            if formula: var.set('수식: '+value)
            self.fields[col]=(var,formula)
        self.gridbox.columnconfigure(1,weight=1); self.gridbox.columnconfigure(3,weight=1)
        ttk.Button(self.gridbox,text='시작일 + 사용기간으로 만료일 계산',command=self.calculate).grid(row=10,column=0,columnspan=4,sticky='w',pady=14)
        if self.item:
            ttk.Label(self.gridbox,text=f"원본 위치: {self.item['sheet']} / {self.item['row']}행 · 구분 이동은 이번 버전에서 지원하지 않습니다.",foreground='#697c90').grid(row=11,column=0,columnspan=4,sticky='w')

    def calculate(self):
        try:
            if self.fields[15][1]: raise ValueError('기존 만료일은 수식입니다. 엑셀에서 자동 계산됩니다.')
            start=as_date(self.fields[14][0].get()); months=int(self.fields[16][0].get())
            if not start or not 1<=months<=1200: raise ValueError('시작일과 사용기간(1~1200개월)을 확인하세요.')
            self.fields[15][0].set(display(add_months(start,months)))
        except Exception as exc: messagebox.showerror('계산 실패',str(exc),parent=self)

    def apply(self):
        try:
            fields={}
            for col,(var,formula) in self.fields.items():
                if formula or col in (2,17): continue
                value=var.get().strip(); original=self.item['values'].get(col) if self.item else None
                if self.item and value==display(original): continue
                if col in (14,15) and value:
                    parsed=as_date(value)
                    if not parsed:
                        if col==14 and value=='미취득': pass
                        else: raise ValueError('날짜는 YYYY-MM-DD 형식으로 입력하세요. 시작일에는 미취득도 가능합니다.')
                    else: value=parsed
                if col==16 and value:
                    value=int(value)
                    if not 1<=value<=1200: raise ValueError('사용기간은 1~1200개월입니다.')
                # Explicit string type prevents formula injection for ordinary text fields.
                if isinstance(value,str) and value.startswith('='): raise ValueError('일반 입력란에는 수식을 입력할 수 없습니다.')
                fields[col]=value if value!='' else None
            # Duplicate check needs the S/N even for unchanged records.
            if 5 not in fields: fields[5]=self.item['values'].get(5) if self.item else None
            start=as_date(fields.get(14,self.item['values'].get(14) if self.item else None))
            end=as_date(fields.get(15,self.item['values'].get(15) if self.item else None))
            if start and end and end<start: raise ValueError('만료일이 시작일보다 빠릅니다.')
            self.app.store.apply(self.sheet.get(),self.item['row'] if self.item else None,fields)
            self.app.refresh(); self.destroy()
        except Exception as exc: messagebox.showerror('입력 확인',str(exc),parent=self)

if __name__=='__main__':
    app=App()
    def on_error(kind,error,tb):
        log=CONFIG.parent/'error.log'; log.parent.mkdir(parents=True,exist_ok=True)
        log.write_text(''.join(traceback.format_exception(kind,error,tb)),encoding='utf-8')
        messagebox.showerror('오류',f'{error}\n\n오류 기록: {log}',parent=app)
    app.report_callback_exception=on_error
    app.mainloop()
