Set(varSearch, Trim(txtSearch.Text));
Set(varSearchKey,
    Upper(Substitute(Substitute(Substitute(Substitute(Substitute(varSearch,
      " ", ""), Char(160), ""), Char(9), ""), Char(10), ""), Char(13), ""))
);
