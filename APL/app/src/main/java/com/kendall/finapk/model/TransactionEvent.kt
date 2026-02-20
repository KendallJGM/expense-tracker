package com.kendall.finapk.model

data class TransactionEvent(
    val source: String,
    val amount: Int,
    val merchant: String,
    val txDate: String,
    val txTime: String,
    val rawText: String
)
