package com.kendall.finapk.ingestion

import com.kendall.finapk.model.TransactionEvent
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.regex.Pattern

object NotificationParser {
    private val amountPatterns = listOf(
        Pattern.compile("(?:CRC|₡)\\s*([0-9][0-9.,]*)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("([0-9][0-9.,]*)\\s*(?:CRC|colones?)", Pattern.CASE_INSENSITIVE)
    )

    fun parseWallet(raw: String): TransactionEvent? {
        val amount = parseAmount(raw) ?: return null
        val now = Date()
        return TransactionEvent(
            source = "wallet",
            amount = amount,
            merchant = parseMerchant(raw),
            txDate = SimpleDateFormat("yyyy-MM-dd", Locale.US).format(now),
            txTime = SimpleDateFormat("HH:mm:ss", Locale.US).format(now),
            rawText = raw
        )
    }

    fun parseBcrEmailNotification(raw: String): TransactionEvent? {
        val lowered = raw.lowercase(Locale.ROOT)
        if (!(lowered.contains("bcr") && (lowered.contains("transfer") || lowered.contains("compra")))) {
            return null
        }
        val amount = parseAmount(raw) ?: return null
        val now = Date()
        return TransactionEvent(
            source = "email",
            amount = amount,
            merchant = parseMerchant(raw),
            txDate = SimpleDateFormat("yyyy-MM-dd", Locale.US).format(now),
            txTime = SimpleDateFormat("HH:mm:ss", Locale.US).format(now),
            rawText = raw
        )
    }

    private fun parseAmount(raw: String): Int? {
        for (pattern in amountPatterns) {
            val match = pattern.matcher(raw)
            if (match.find()) {
                val normalized = match.group(1)?.replace(",", "") ?: continue
                return normalized.toDoubleOrNull()?.toInt()
            }
        }
        return null
    }

    private fun parseMerchant(raw: String): String {
        val merchantPatterns = listOf(
            Pattern.compile("(?:en|comercio|at)\\s+([A-Za-z0-9 ._-]{3,})", Pattern.CASE_INSENSITIVE),
            Pattern.compile("(?:merchant|establecimiento)\\s*[:\\-]\\s*([A-Za-z0-9 ._-]{3,})", Pattern.CASE_INSENSITIVE)
        )
        for (pattern in merchantPatterns) {
            val match = pattern.matcher(raw)
            if (match.find()) return match.group(1).trim().trimEnd('.')
        }
        return "Transacción"
    }
}
