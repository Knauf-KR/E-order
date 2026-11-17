// Server repeats this business rule. Preview alone never writes a record.
With(
    {months: IfError(Value(txtMonths.Text), Blank())},
    If(
        chkHasStart.Value && !IsBlank(months) && months >= 1 && months <= 1200 && Mod(months,1) = 0,
        With(
            {monthStart: DateAdd(Date(Year(dpStart.SelectedDate), Month(dpStart.SelectedDate), 1), months, TimeUnit.Months)},
            Text(
                Date(Year(monthStart), Month(monthStart),
                    Min(Day(dpStart.SelectedDate), Day(DateAdd(DateAdd(monthStart, 1, TimeUnit.Months), -1, TimeUnit.Days)))),
                "[$-en-US]yyyy-mm-dd"
            )
        ),
        "계산할 시작일과 사용기간을 입력하세요."
    )
)
