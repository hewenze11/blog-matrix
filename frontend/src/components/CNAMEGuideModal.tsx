'use client'

interface CNAMEInfo {
  blog_name: string
  pages_domain: string
  custom_domain: string
  cname_record: { type: string; host: string; value: string }
  cname_www_record: { type: string; host: string; value: string }
  guide_message: string
}

interface Props {
  info: CNAMEInfo
  onClose: () => void
  onBind: () => void
}

const DNS_GUIDES = [
  {
    name: '阿里云',
    icon: '🅰',
    color: 'text-orange-500',
    steps: ['登录阿里云控制台 → 域名', '找到您的域名，点击「解析」', '添加记录：类型 CNAME，主机记录 @，记录值如下'],
  },
  {
    name: '腾讯云/DNSPod',
    icon: '🐧',
    color: 'text-blue-500',
    steps: ['登录腾讯云控制台 → DNS解析', '选择您的域名，点击「添加记录」', '记录类型选 CNAME，主机记录填 @，记录值如下'],
  },
  {
    name: 'GoDaddy',
    icon: '🦊',
    color: 'text-green-600',
    steps: ['登录 GoDaddy → My Domains', '点击域名旁的 DNS → Add New Record', '类型选 CNAME，Name 填 @，Value 填写下方记录值'],
  },
  {
    name: 'Namecheap',
    icon: '🔷',
    color: 'text-indigo-500',
    steps: ['登录 Namecheap → Domain List', '点击 Manage → Advanced DNS → Add New Record', '选择 CNAME Record，Host 填 @，Value 填写下方记录值'],
  },
]

export default function CNAMEGuideModal({ info, onClose, onBind }: Props) {
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="p-6 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-t-2xl">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold">🎉 站点部署成功！</h2>
              <p className="text-blue-100 text-sm mt-1">请完成域名解析配置，让您的域名指向该站点</p>
            </div>
            <button onClick={onClose} className="text-blue-200 hover:text-white text-2xl leading-none">✕</button>
          </div>
        </div>

        <div className="p-6">
          {/* Key Records - 大字突出显示 */}
          <div className="bg-blue-50 border-2 border-blue-200 rounded-xl p-5 mb-6">
            <h3 className="text-base font-bold text-blue-800 mb-4 flex items-center gap-2">
              <span>📋</span> 请在您的域名服务商添加以下 DNS 记录
            </h3>
            <div className="space-y-3">
              {[info.cname_record, info.cname_www_record].map((record, i) => (
                <div key={i} className="bg-white rounded-lg p-4 border border-blue-100 grid grid-cols-3 gap-4">
                  <div>
                    <div className="text-xs text-gray-400 mb-1">记录类型</div>
                    <div className="text-xl font-bold text-blue-600">{record.type}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 mb-1">主机记录</div>
                    <div className="text-xl font-bold text-gray-800">{record.host}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 mb-1">记录值（CNAME 目标）</div>
                    <div className="text-sm font-bold text-gray-800 break-all font-mono bg-gray-50 p-2 rounded border">
                      {record.value}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <p className="text-xs text-blue-600 mt-3">
              💡 通常添加 @ 记录即可（根域名）；如需 www 子域名也能访问，可同时添加 www 记录
            </p>
          </div>

          {/* Provider Guides */}
          <div className="mb-6">
            <h3 className="text-base font-semibold text-gray-800 mb-3">各平台操作指引</h3>
            <div className="grid grid-cols-2 gap-3">
              {DNS_GUIDES.map(guide => (
                <div key={guide.name} className="border border-gray-200 rounded-xl p-4">
                  <div className={`font-semibold mb-2 flex items-center gap-1.5 ${guide.color}`}>
                    <span>{guide.icon}</span> {guide.name}
                  </div>
                  <ol className="space-y-1">
                    {guide.steps.map((step, i) => (
                      <li key={i} className="text-xs text-gray-600 flex gap-1.5">
                        <span className="text-gray-400 flex-shrink-0">{i + 1}.</span>
                        <span>{step}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              ))}
            </div>
          </div>

          {/* Blog Info */}
          <div className="bg-gray-50 rounded-xl p-4 mb-6 text-sm">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <span className="text-gray-400">博客名称：</span>
                <span className="font-medium text-gray-800">{info.blog_name}</span>
              </div>
              <div>
                <span className="text-gray-400">Pages 域名：</span>
                <a href={`https://${info.pages_domain}`} target="_blank" rel="noopener noreferrer"
                   className="font-mono text-blue-500 hover:underline text-xs">{info.pages_domain}</a>
              </div>
              <div>
                <span className="text-gray-400">目标域名：</span>
                <span className="font-medium text-gray-800">{info.custom_domain}</span>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button onClick={onClose}
              className="flex-1 py-3 border border-gray-300 text-gray-700 rounded-xl font-medium hover:bg-gray-50 transition-colors text-sm">
              稍后配置
            </button>
            <button onClick={onBind}
              className="flex-2 flex-1 py-3 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 transition-colors text-sm flex items-center justify-center gap-2">
              ✅ 我已解析，立即绑定域名
            </button>
          </div>
          <p className="text-xs text-gray-400 text-center mt-3">
            点击绑定后，Cloudflare 将验证 DNS 解析。DNS 生效通常需要 5-10 分钟
          </p>
        </div>
      </div>
    </div>
  )
}
