import nodemailer from 'nodemailer'

let transporter: nodemailer.Transporter | null = null

function getTransporter(): nodemailer.Transporter | null {
  if (transporter) return transporter
  const host = process.env.SMTP_HOST
  if (!host) return null // 未配置 SMTP → dev 模式，日志输出代替发信
  transporter = nodemailer.createTransport({
    host,
    port: Number(process.env.SMTP_PORT) || 587,
    secure: (Number(process.env.SMTP_PORT) || 587) === 465,
    auth: {
      user: process.env.SMTP_USER,
      pass: process.env.SMTP_PASS,
    },
  })
  return transporter
}

export async function sendMail(to: string, subject: string, html: string) {
  const from = process.env.SMTP_FROM || 'KS2 Wiki <noreply@localhost>'
  const t = getTransporter()
  if (!t) {
    console.log('[DEV-EMAIL] 未配置 SMTP，邮件内容如下:')
    console.log(`  To: ${to}`)
    console.log(`  Subject: ${subject}`)
    console.log(`  Body: ${html}`)
    return
  }
  await t.sendMail({ from, to, subject, html })
}