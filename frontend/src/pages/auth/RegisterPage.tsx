const RegisterPage = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 flex items-center justify-center p-4">
      <div className="bg-gray-800 p-8 rounded-2xl shadow-2xl border border-gray-700 max-w-md w-full">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-white mb-2">Create Account</h2>
          <p className="text-gray-400">Join DTrade and start trading</p>
        </div>
        
        <div className="space-y-4">
          <input
            type="text"
            placeholder="Full Name"
            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="email"
            placeholder="Email Address"
            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="password"
            placeholder="Password"
            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg transition-colors">
            Create Account
          </button>
        </div>
        
        <div className="mt-6 text-center">
          <p className="text-gray-400">
            Already have an account?{' '}
            <a href="/login" className="text-blue-400 hover:text-blue-300">Sign in</a>
          </p>
        </div>
      </div>
    </div>
  )
}

export default RegisterPage
