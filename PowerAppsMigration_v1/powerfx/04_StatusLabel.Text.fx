Switch(
    true,
    ThisItem.IsDeleted, "삭제",
    ThisItem.LifecycleState = "Retired", "폐기완료",
    ThisItem.HasExpiry = false, "날짜 미등록",
    ThisItem.ExpiryDate < varToday, "만료",
    ThisItem.ExpiryDate <= DateAdd(varToday, 30, TimeUnit.Days), "30일 이내",
    ThisItem.ExpiryDate <= DateAdd(varToday, 60, TimeUnit.Days), "60일 이내",
    ThisItem.ExpiryDate <= DateAdd(varToday, 90, TimeUnit.Days), "90일 이내",
    "정상"
)
