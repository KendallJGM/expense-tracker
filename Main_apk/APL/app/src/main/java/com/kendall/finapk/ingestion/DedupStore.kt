package com.kendall.finapk.ingestion

import android.content.Context

class DedupStore(context: Context) {
    private val prefs = context.getSharedPreferences("fin_dedup", Context.MODE_PRIVATE)

    fun shouldSend(userId: String, txDate: String, amount: Int, merchant: String): Boolean {
        val key = "$userId|$txDate|$amount|${merchant.trim().lowercase()}"
        if (prefs.contains(key)) return false
        prefs.edit().putLong(key, System.currentTimeMillis()).apply()
        return true
    }
}
