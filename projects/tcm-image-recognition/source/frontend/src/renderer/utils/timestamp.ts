import { ref, computed } from 'vue'

interface DateComponents {
    year?: number
    month?: number
    day?: number
    hour?: number
    minute?: number
    second?: number
}

export const createFromComponents = (components: DateComponents): Date => {
    return new Date(
        components.year || 0,
        components.month ? components.month - 1 : 0,
        components.day || 1,
        components.hour || 0,
        components.minute || 0,
        components.second || 0
    )
}

/**
 * Format a Date object to string
 */
export const formatDate = (date: Date, formatString = 'yyyy-MM-dd'): string => {
    const pad = (num: number): string => num.toString().padStart(2, '0')

    return formatString
        .replace(/yyyy/g, date.getFullYear().toString())
        .replace(/MM/g, pad(date.getMonth() + 1))
        .replace(/dd/g, pad(date.getDate()))
        .replace(/HH/g, pad(date.getHours()))
        .replace(/mm/g, pad(date.getMinutes()))
        .replace(/ss/g, pad(date.getSeconds()))
}

export function renderTime(date:any) {
    var dateee = new Date(date).toJSON();
    return new Date(+new Date(dateee) + 8 * 3600 * 1000).toISOString().replace(/T/g, ' ').replace(/\.[\d]{3}Z/, '')
}


/**
 * Parse string to Date object
 */
export const parseDate = (dateString: string, format?: string): Date => {
    if (format) {
        const parts: Record<string, number> = {}
        const formatParts = format.match(/(yyyy|MM|dd|HH|mm|ss)/g) || []
        const valueParts = dateString.split(/[^0-9]/)

        formatParts.forEach((part, i) => {
            parts[part] = parseInt(valueParts[i], 10)
        })

        return createFromComponents({
            year: parts['yyyy'],
            month: parts['MM'],
            day: parts['dd'],
            hour: parts['HH'],
            minute: parts['mm'],
            second: parts['ss']
        })
    }
    return new Date(dateString)
}

/**
 * Get date components from Date object
 */
export const getComponents = (date: Date): DateComponents => {
    return {
        year: date.getFullYear(),
        month: date.getMonth() + 1,
        day: date.getDate(),
        hour: date.getHours(),
        minute: date.getMinutes(),
        second: date.getSeconds()
    }
}
