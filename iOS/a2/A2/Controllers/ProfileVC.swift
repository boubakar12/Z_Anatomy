//
//  ProfileVC.swift
//  A2
// Boubakar Diallo
//  Created by Vin Bui on 6/4/23.
//
import UIKit

class ProfileVC: UIViewController {
	
	private let profileImageView: UIImageView = {
		let imageView = UIImageView()
		imageView.translatesAutoresizingMaskIntoConstraints = false
		imageView.layer.cornerRadius = 64
		imageView.layer.masksToBounds = true
		imageView.image = UIImage(named: "profile")
		return imageView
	}()
	
	private let additionalImageView: UIImageView = {
		let imageView = UIImageView()
		imageView.translatesAutoresizingMaskIntoConstraints = false
		imageView.layer.cornerRadius = 40
		imageView.layer.masksToBounds = true
		imageView.image = UIImage(named: "profilePicture")
		return imageView
	}()
	
	private let nameLabel: UILabel = {
		let label = UILabel()
		label.translatesAutoresizingMaskIntoConstraints = false
		label.text = "Boubakar Diallo"
		label.font = .systemFont(ofSize: 16, weight: .semibold)
		label.textColor = UIColor.a2.ruby
		label.textAlignment = .center
		return label
	}()
	
	private let bioLabel: UILabel = {
		let label = UILabel()
		label.translatesAutoresizingMaskIntoConstraints = false
		label.text = "Born and raise in Guinea, Move to the U.S in 2022 and interested in learning CS and ECE and also doing Project Team"
		label.font = .italicSystemFont(ofSize: 16)
		label.numberOfLines = 0
		label.textAlignment = .center
		return label
	}()
	
	private let hometownIcon: UIImageView = {
		let imageView = UIImageView()
		imageView.translatesAutoresizingMaskIntoConstraints = false
		imageView.image = UIImage(systemName: "house.fill")
		return imageView
	}()
	
	private let hometownLabel: UILabel = {
		let label = UILabel()
		label.translatesAutoresizingMaskIntoConstraints = false
		label.text = "Quincy, MA"
		label.font = .systemFont(ofSize: 16)
		return label
	}()
	
	private let majorIcon: UIImageView = {
		let imageView = UIImageView()
		imageView.translatesAutoresizingMaskIntoConstraints = false
		imageView.image = UIImage(systemName: "book.fill") 
		return imageView
	}()
	
	private let majorLabel: UILabel = {
		let label = UILabel()
		label.translatesAutoresizingMaskIntoConstraints = false
		label.text = "Electrical and Computer Engineering"
		label.font = .systemFont(ofSize: 16)
		return label
	}()
	
	private let editProfileButton: UIButton = {
		let button = UIButton()
		button.translatesAutoresizingMaskIntoConstraints = false
		button.setTitle("Edit Profile", for: .normal)
		button.setTitleColor(.white, for: .normal)
		button.backgroundColor = UIColor.a2.ruby
		button.layer.cornerRadius = 16
		button.addTarget(self, action: #selector(editProfileTapped), for: .touchUpInside)
		return button
	}()
	
	override func viewDidLoad() {
		super.viewDidLoad()
		view.backgroundColor = .white
		title = "My Profile"
		
		setupViews()
	}
	
	private func setupViews() {
		view.addSubview(profileImageView)
		view.addSubview(additionalImageView)
		view.addSubview(nameLabel)
		view.addSubview(bioLabel)
		view.addSubview(hometownIcon)
		view.addSubview(hometownLabel)
		view.addSubview(majorIcon)
		view.addSubview(majorLabel)
		view.addSubview(editProfileButton)
		
		NSLayoutConstraint.activate([
			profileImageView.centerXAnchor.constraint(equalTo: view.centerXAnchor),
			profileImageView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 32),
			profileImageView.widthAnchor.constraint(equalToConstant: 128),
			profileImageView.heightAnchor.constraint(equalToConstant: 30),
			
			additionalImageView.centerXAnchor.constraint(equalTo: view.centerXAnchor),
			additionalImageView.topAnchor.constraint(equalTo: profileImageView.bottomAnchor, constant: 16),
			additionalImageView.widthAnchor.constraint(equalToConstant: 80),
			additionalImageView.heightAnchor.constraint(equalToConstant: 80),
			
			nameLabel.topAnchor.constraint(equalTo: additionalImageView.bottomAnchor, constant: 16),
			nameLabel.centerXAnchor.constraint(equalTo: view.centerXAnchor),
			
			bioLabel.topAnchor.constraint(equalTo: nameLabel.bottomAnchor, constant: 16),
			bioLabel.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 32),
			bioLabel.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -32),
			
			hometownIcon.topAnchor.constraint(equalTo: bioLabel.bottomAnchor, constant: 16),
			hometownIcon.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 32),
			hometownIcon.widthAnchor.constraint(equalToConstant: 24),
			hometownIcon.heightAnchor.constraint(equalToConstant: 24),
			
			hometownLabel.centerYAnchor.constraint(equalTo: hometownIcon.centerYAnchor),
			hometownLabel.leadingAnchor.constraint(equalTo: hometownIcon.trailingAnchor, constant: 8),
			
			majorIcon.topAnchor.constraint(equalTo: hometownIcon.bottomAnchor, constant: 16),
			majorIcon.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 32),
			majorIcon.widthAnchor.constraint(equalToConstant: 24),
			majorIcon.heightAnchor.constraint(equalToConstant: 24),
			
			majorLabel.centerYAnchor.constraint(equalTo: majorIcon.centerYAnchor),
			majorLabel.leadingAnchor.constraint(equalTo: majorIcon.trailingAnchor, constant: 8),
			
			editProfileButton.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 32),
			editProfileButton.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -32),
			editProfileButton.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -32),
			editProfileButton.heightAnchor.constraint(equalToConstant: 56)
		])
	}
	
	@objc private func editProfileTapped() {
		let editProfileVC = EditProfileVC()
		navigationController?.pushViewController(editProfileVC, animated: true)
	}
}
