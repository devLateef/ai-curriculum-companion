import { useState } from 'react'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="min-h-screen bg-linear-to-br from-indigo-50 via-white to-cyan-50 flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl overflow-hidden transform transition-all hover:scale-[1.02] duration-300">
        <div className="p-8">
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center animate-bounce">
              <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
          </div>
          
          <h1 className="text-3xl font-extrabold text-center text-gray-900 mb-2 tracking-tight">
            AI Curriculum
          </h1>
          <p className="text-center text-gray-500 mb-8 font-medium">
            Next generation learning experience
          </p>
          
          <div className="space-y-4">
            <button 
              onClick={() => setCount((count) => count + 1)}
              className="w-full bg-linear-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold py-3 px-4 rounded-xl shadow-md transition-all duration-200 flex items-center justify-center gap-2 active:scale-95 cursor-pointer"
            >
              <span>Explore Courses</span>
              <span className="bg-white/20 px-2 py-0.5 rounded-full text-sm">
                {count}
              </span>
            </button>
            
            <button className="w-full bg-white border-2 border-gray-100 hover:border-gray-200 hover:bg-gray-50 text-gray-700 font-semibold py-3 px-4 rounded-xl transition-all duration-200 cursor-pointer">
              View Documentation
            </button>
          </div>
        </div>
        
        <div className="bg-gray-50 p-4 border-t border-gray-100 text-center">
          <p className="text-sm text-gray-500">
            React + TypeScript + Tailwind v4
          </p>
        </div>
      </div>
    </div>
  )
}

export default App
